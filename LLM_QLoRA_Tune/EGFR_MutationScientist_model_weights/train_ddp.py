
import os
import gc
import json
import math
import random
import argparse
from contextlib import nullcontext

import numpy as np
import torch
import torch.distributed as dist
import bitsandbytes as bnb

from torch.utils.data import Dataset, DataLoader
from torch.utils.data.distributed import DistributedSampler
from torch.nn.parallel import DistributedDataParallel as DDP

from transformers import (
    AutoTokenizer,
    BitsAndBytesConfig,
    Qwen3_5ForConditionalGeneration,
    get_cosine_schedule_with_warmup,
)

from peft import (
    LoraConfig,
    get_peft_model,
    prepare_model_for_kbit_training,
)


# ============================================================
# CONFIGURATION
# ============================================================

MODEL_ID = "Qwen/Qwen3.5-4B"

DATA_PATH = "/kaggle/working/egfr_encoded_data.pt"
OUTPUT_DIR = "/kaggle/working/egfr_qwen35_qlora_ddp"

SEED = 42
EPOCHS = 3

MICRO_BATCH_SIZE = 1
GRAD_ACCUM = 4

LEARNING_RATE = 1e-4
WEIGHT_DECAY = 0.01
MAX_GRAD_NORM = 1.0

NUM_WORKERS = 0


# ============================================================
# DISTRIBUTED SETUP
# ============================================================

def setup_distributed():
    dist.init_process_group(backend="nccl")

    local_rank = int(os.environ["LOCAL_RANK"])
    rank = dist.get_rank()
    world_size = dist.get_world_size()

    torch.cuda.set_device(local_rank)

    return local_rank, rank, world_size


def cleanup_distributed():
    dist.destroy_process_group()


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


# ============================================================
# DATASET AND COLLATOR
# ============================================================

class EGFRDataset(Dataset):
    def __init__(self, rows):
        self.rows = rows

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, idx):
        return self.rows[idx]


class CompletionOnlyCollator:
    def __init__(self, pad_token_id):
        self.pad_token_id = pad_token_id

    def __call__(self, batch):
        max_len = max(len(x["input_ids"]) for x in batch)
        batch_size = len(batch)

        input_ids = torch.full(
            (batch_size, max_len),
            self.pad_token_id,
            dtype=torch.long,
        )

        labels = torch.full(
            (batch_size, max_len),
            -100,
            dtype=torch.long,
        )

        attention_mask = torch.zeros(
            (batch_size, max_len),
            dtype=torch.long,
        )

        for i, item in enumerate(batch):
            length = len(item["input_ids"])

            input_ids[i, :length] = torch.tensor(
                item["input_ids"], dtype=torch.long
            )

            labels[i, :length] = torch.tensor(
                item["labels"], dtype=torch.long
            )

            attention_mask[i, :length] = 1

        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels,
        }


# ============================================================
# MODEL LOADING
# ============================================================

def load_model(local_rank):

    print(f"[GPU {local_rank}] Loading tokenizer...", flush=True)

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_ID,
        padding_side="right",
    )

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )

    print(f"[GPU {local_rank}] Loading quantised model...", flush=True)

    model = Qwen3_5ForConditionalGeneration.from_pretrained(
        MODEL_ID,
        quantization_config=bnb_config,
        torch_dtype=torch.float16,
        device_map={"": local_rank},
        low_cpu_mem_usage=True,
    )

    model.config.use_cache = False
    model.config.text_config.use_cache = False

    # Target every Linear module in the language backbone,
    # matching the successful single-GPU LoRA configuration.
    language_linear_modules = [
        name
        for name, module in model.named_modules()
        if isinstance(module, torch.nn.Linear)
        and name.startswith("model.language_model.")
    ]

    if not language_linear_modules:
        raise RuntimeError("No language-model Linear modules found.")

    print(
        f"[GPU {local_rank}] LoRA targets: "
        f"{len(language_linear_modules)}",
        flush=True,
    )

    model = prepare_model_for_kbit_training(
        model,
        use_gradient_checkpointing=True,
        gradient_checkpointing_kwargs={
            "use_reentrant": False
        },
    )

    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        target_modules=language_linear_modules,
        task_type="CAUSAL_LM",
    )

    model = get_peft_model(model, lora_config)

    model.print_trainable_parameters()

    return model, tokenizer


# ============================================================
# VALIDATION
# ============================================================

@torch.no_grad()
def evaluate(model, val_loader, device):

    model.eval()

    total_loss = 0.0
    total_tokens = 0

    for batch in val_loader:

        batch = {
            key: value.to(device, non_blocking=True)
            for key, value in batch.items()
        }

        with torch.autocast(
            device_type="cuda",
            dtype=torch.float16,
        ):
            outputs = model(**batch)

        valid_tokens = batch["labels"].ne(-100).sum().item()

        total_loss += outputs.loss.item() * valid_tokens
        total_tokens += valid_tokens

    model.train()

    return total_loss / max(total_tokens, 1)


# ============================================================
# MAIN
# ============================================================

def main():

    local_rank, rank, world_size = setup_distributed()
    device = torch.device(f"cuda:{local_rank}")

    set_seed(SEED + rank)

    if rank == 0:
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    dist.barrier()

    # --------------------------------------------------------
    # Load data
    # --------------------------------------------------------

    data = torch.load(
        DATA_PATH,
        map_location="cpu",
        weights_only=False,
    )

    train_dataset = EGFRDataset(data["train"])
    val_dataset = EGFRDataset(data["validation"])

    train_sampler = DistributedSampler(
        train_dataset,
        num_replicas=world_size,
        rank=rank,
        shuffle=True,
        seed=SEED,
        drop_last=False,
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=MICRO_BATCH_SIZE,
        sampler=train_sampler,
        collate_fn=None,
        num_workers=NUM_WORKERS,
        pin_memory=True,
        drop_last=False,
    )

    # --------------------------------------------------------
    # Load model independently on each GPU
    # --------------------------------------------------------

    model, tokenizer = load_model(local_rank)

    collator = CompletionOnlyCollator(tokenizer.pad_token_id)
    train_loader.collate_fn = collator

    # Only rank 0 performs validation, using the complete
    # validation set without distributed-sampler duplication.
    val_loader = None

    if rank == 0:
        val_loader = DataLoader(
            val_dataset,
            batch_size=1,
            shuffle=False,
            collate_fn=collator,
            num_workers=0,
            pin_memory=True,
        )

    # --------------------------------------------------------
    # Wrap with DDP
    # --------------------------------------------------------

    model = DDP(
        model,
        device_ids=[local_rank],
        output_device=local_rank,
        find_unused_parameters=False,
        broadcast_buffers=False,
        gradient_as_bucket_view=True,
    )

    trainable_params = [
        p for p in model.parameters() if p.requires_grad
    ]

    optimizer = bnb.optim.PagedAdamW8bit(
        trainable_params,
        lr=LEARNING_RATE,
        betas=(0.9, 0.999),
        weight_decay=WEIGHT_DECAY,
    )

    steps_per_epoch = math.ceil(
        len(train_loader) / GRAD_ACCUM
    )

    total_steps = steps_per_epoch * EPOCHS
    warmup_steps = max(1, int(total_steps * 0.05))

    scheduler = get_cosine_schedule_with_warmup(
        optimizer,
        num_warmup_steps=warmup_steps,
        num_training_steps=total_steps,
    )

    scaler = torch.amp.GradScaler("cuda")

    if rank == 0:
        print("\n========== TRAINING CONFIGURATION ==========")
        print("World size:", world_size)
        print("Training examples:", len(train_dataset))
        print("Validation examples:", len(val_dataset))
        print("Micro-batch per GPU:", MICRO_BATCH_SIZE)
        print("Gradient accumulation:", GRAD_ACCUM)
        print("Effective global batch:", MICRO_BATCH_SIZE * GRAD_ACCUM * world_size)
        print("Steps per epoch:", steps_per_epoch)
        print("Total optimiser steps:", total_steps)
        print("Warmup steps:", warmup_steps)
        print("============================================\n")

    best_val_loss = float("inf")
    history = []

    # --------------------------------------------------------
    # Training
    # --------------------------------------------------------

    for epoch in range(EPOCHS):

        train_sampler.set_epoch(epoch)
        model.train()

        optimizer.zero_grad(set_to_none=True)

        epoch_loss = 0.0
        epoch_tokens = 0

        num_batches = len(train_loader)

        for step, batch in enumerate(train_loader):

            batch = {
                key: value.to(device, non_blocking=True)
                for key, value in batch.items()
            }

            group_start = (step // GRAD_ACCUM) * GRAD_ACCUM
            group_end = min(group_start + GRAD_ACCUM, num_batches)
            group_size = group_end - group_start

            is_sync_step = (step + 1 == group_end)

            sync_context = (
                nullcontext()
                if is_sync_step
                else model.no_sync()
            )

            with sync_context:

                with torch.autocast(
                    device_type="cuda",
                    dtype=torch.float16,
                ):
                    outputs = model(**batch)
                    loss = outputs.loss

                valid_tokens = batch["labels"].ne(-100).sum().item()

                epoch_loss += loss.detach().item() * valid_tokens
                epoch_tokens += valid_tokens

                scaled_loss = loss / group_size
                scaler.scale(scaled_loss).backward()

            if is_sync_step:

                scaler.unscale_(optimizer)

                torch.nn.utils.clip_grad_norm_(
                    trainable_params,
                    MAX_GRAD_NORM,
                )

                scaler.step(optimizer)
                scaler.update()

                optimizer.zero_grad(set_to_none=True)
                scheduler.step()

            if rank == 0 and (step + 1) % 50 == 0:
                print(
                    f"Epoch {epoch + 1}/{EPOCHS} | "
                    f"Batch {step + 1}/{num_batches} | "
                    f"Loss {loss.item():.4f} | "
                    f"LR {scheduler.get_last_lr()[0]:.2e}",
                    flush=True,
                )

        # ----------------------------------------------------
        # Aggregate training loss across GPUs
        # ----------------------------------------------------

        stats = torch.tensor(
            [epoch_loss, epoch_tokens],
            dtype=torch.float64,
            device=device,
        )

        dist.all_reduce(stats, op=dist.ReduceOp.SUM)

        train_loss = (stats[0] / stats[1]).item()

        # ----------------------------------------------------
        # Validation on rank 0
        # ----------------------------------------------------

        dist.barrier()

        if rank == 0:

            val_loss = evaluate(
                model.module,
                val_loader,
                device,
            )

            print(
                f"\nEpoch {epoch + 1}/{EPOCHS} complete | "
                f"Train loss: {train_loss:.5f} | "
                f"Validation loss: {val_loss:.5f}",
                flush=True,
            )

            history.append({
                "epoch": epoch + 1,
                "train_loss": train_loss,
                "validation_loss": val_loss,
            })

            if val_loss < best_val_loss:

                best_val_loss = val_loss

                best_dir = os.path.join(
                    OUTPUT_DIR,
                    "best_adapter",
                )

                model.module.save_pretrained(best_dir)
                tokenizer.save_pretrained(best_dir)

                print(
                    f"Saved new best adapter: {best_dir}",
                    flush=True,
                )

            with open(
                os.path.join(OUTPUT_DIR, "training_history.json"),
                "w",
            ) as f:
                json.dump(history, f, indent=2)

        dist.barrier()

        gc.collect()
        torch.cuda.empty_cache()

    if rank == 0:
        print("\nTraining completed.")
        print("Best validation loss:", best_val_loss)
        print("Best adapter:", os.path.join(OUTPUT_DIR, "best_adapter"))

    dist.barrier()
    cleanup_distributed()


if __name__ == "__main__":
    main()
