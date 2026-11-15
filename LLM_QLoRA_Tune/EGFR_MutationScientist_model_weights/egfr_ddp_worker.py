
import os
import gc
import json
import math
import argparse
from contextlib import nullcontext

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
        n = len(batch)

        input_ids = torch.full(
            (n, max_len), self.pad_token_id, dtype=torch.long
        )
        labels = torch.full(
            (n, max_len), -100, dtype=torch.long
        )
        attention_mask = torch.zeros(
            (n, max_len), dtype=torch.long
        )

        for i, item in enumerate(batch):
            length = len(item["input_ids"])
            input_ids[i, :length] = torch.tensor(item["input_ids"])
            labels[i, :length] = torch.tensor(item["labels"])
            attention_mask[i, :length] = 1

        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels,
        }


def evaluate(model, loader, device):
    model.eval()
    total_loss = 0.0
    total_tokens = 0

    with torch.no_grad():
        for batch in loader:
            batch = {
                k: v.to(device, non_blocking=True)
                for k, v in batch.items()
            }

            with torch.autocast("cuda", dtype=torch.float16):
                output = model(**batch)

            n_tokens = batch["labels"].ne(-100).sum().item()
            total_loss += output.loss.item() * n_tokens
            total_tokens += n_tokens

    model.train()
    return total_loss / max(total_tokens, 1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", required=True)
    parser.add_argument("--val", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--lr", type=float, required=True)
    parser.add_argument("--dropout", type=float, required=True)
    parser.add_argument("--weight_decay", type=float, required=True)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--patience", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    dist.init_process_group("nccl")
    rank = dist.get_rank()
    world_size = dist.get_world_size()
    local_rank = int(os.environ["LOCAL_RANK"])

    torch.cuda.set_device(local_rank)
    device = torch.device(f"cuda:{local_rank}")

    torch.manual_seed(args.seed + rank)

    if rank == 0:
        os.makedirs(args.output, exist_ok=True)

    dist.barrier()

    train_rows = torch.load(
        args.train, map_location="cpu", weights_only=False
    )
    val_rows = torch.load(
        args.val, map_location="cpu", weights_only=False
    )

    train_dataset = EGFRDataset(train_rows)
    val_dataset = EGFRDataset(val_rows)

    tokenizer = AutoTokenizer.from_pretrained(
        "Qwen/Qwen3.5-4B",
        padding_side="right"
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    collator = CompletionOnlyCollator(tokenizer.pad_token_id)

    train_sampler = DistributedSampler(
        train_dataset,
        num_replicas=world_size,
        rank=rank,
        shuffle=True,
        seed=args.seed
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=1,
        sampler=train_sampler,
        collate_fn=collator,
        num_workers=0,
        pin_memory=True
    )

    val_loader = None
    if rank == 0:
        val_loader = DataLoader(
            val_dataset,
            batch_size=1,
            shuffle=False,
            collate_fn=collator,
            num_workers=0,
            pin_memory=True
        )

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True
    )

    model = Qwen3_5ForConditionalGeneration.from_pretrained(
        "Qwen/Qwen3.5-4B",
        quantization_config=bnb_config,
        torch_dtype=torch.float16,
        device_map={"": local_rank},
        low_cpu_mem_usage=True
    )

    model.config.use_cache = False
    model.config.text_config.use_cache = False

    language_linear_modules = [
        name for name, module in model.named_modules()
        if isinstance(module, torch.nn.Linear)
        and name.startswith("model.language_model.")
    ]

    model = prepare_model_for_kbit_training(
        model,
        use_gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False}
    )

    model = get_peft_model(
        model,
        LoraConfig(
            r=16,
            lora_alpha=32,
            lora_dropout=args.dropout,
            bias="none",
            target_modules=language_linear_modules,
            task_type="CAUSAL_LM"
        )
    )

    model = DDP(
        model,
        device_ids=[local_rank],
        output_device=local_rank,
        find_unused_parameters=False,
        broadcast_buffers=False,
        gradient_as_bucket_view=True
    )

    optimizer = bnb.optim.PagedAdamW8bit(
        [p for p in model.parameters() if p.requires_grad],
        lr=args.lr,
        betas=(0.9, 0.999),
        weight_decay=args.weight_decay
    )

    grad_accum = 4
    steps_per_epoch = math.ceil(len(train_loader) / grad_accum)
    total_steps = steps_per_epoch * args.epochs

    scheduler = get_cosine_schedule_with_warmup(
        optimizer,
        num_warmup_steps=max(1, int(total_steps * 0.05)),
        num_training_steps=total_steps
    )

    scaler = torch.amp.GradScaler("cuda")
    best_val = float("inf")
    patience_count = 0
    history = []

    for epoch in range(args.epochs):
        train_sampler.set_epoch(epoch)
        model.train()
        optimizer.zero_grad(set_to_none=True)

        total_train_loss = 0.0
        total_train_tokens = 0
        num_batches = len(train_loader)

        for step, batch in enumerate(train_loader):
            batch = {
                k: v.to(device, non_blocking=True)
                for k, v in batch.items()
            }

            group_start = (step // grad_accum) * grad_accum
            group_end = min(group_start + grad_accum, num_batches)
            group_size = group_end - group_start
            sync_step = (step + 1 == group_end)

            sync_context = nullcontext() if sync_step else model.no_sync()

            with sync_context:
                with torch.autocast("cuda", dtype=torch.float16):
                    output = model(**batch)
                    loss = output.loss

                n_tokens = batch["labels"].ne(-100).sum().item()
                total_train_loss += loss.detach().item() * n_tokens
                total_train_tokens += n_tokens

                scaler.scale(loss / group_size).backward()

            if sync_step:
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(
                    [p for p in model.parameters() if p.requires_grad],
                    1.0
                )
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad(set_to_none=True)
                scheduler.step()

            if rank == 0 and (step + 1) % 100 == 0:
                print(
                    f"Epoch {epoch+1}/{args.epochs} "
                    f"Batch {step+1}/{num_batches} "
                    f"Loss {loss.item():.4f}",
                    flush=True
                )

        stats = torch.tensor(
            [total_train_loss, total_train_tokens],
            dtype=torch.float64,
            device=device
        )
        dist.all_reduce(stats, op=dist.ReduceOp.SUM)
        train_loss = (stats[0] / stats[1]).item()

        dist.barrier()

        if rank == 0:
            val_loss = evaluate(model.module, val_loader, device)

            print(
                f"Epoch {epoch+1}: train={train_loss:.5f}, "
                f"validation={val_loss:.5f}",
                flush=True
            )

            history.append({
                "epoch": epoch + 1,
                "train_loss": train_loss,
                "validation_loss": val_loss
            })

            if val_loss < best_val:
                best_val = val_loss
                patience_count = 0

                if args.epochs > 1:
                    model.module.save_pretrained(
                        os.path.join(args.output, "best_adapter")
                    )
                    tokenizer.save_pretrained(
                        os.path.join(args.output, "best_adapter")
                    )
            else:
                patience_count += 1

            with open(os.path.join(args.output, "metrics.json"), "w") as f:
                json.dump({
                    "best_validation_loss": best_val,
                    "history": history
                }, f, indent=2)

        # Broadcast early-stopping decision to both processes.
        stop_tensor = torch.tensor(
            [1 if rank == 0 and patience_count >= args.patience else 0],
            device=device
        )
        dist.broadcast(stop_tensor, src=0)

        dist.barrier()

        if stop_tensor.item():
            if rank == 0:
                print("Early stopping triggered.", flush=True)
            break

        gc.collect()
        torch.cuda.empty_cache()

    # For one-epoch CV jobs, record the score without saving an adapter.
    dist.barrier()
    dist.destroy_process_group()


if __name__ == "__main__":
    main()
