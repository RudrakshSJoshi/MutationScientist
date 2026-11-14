# Launch PyMOL from molecular_analysis/structural_analysis.
reinitialize
load pdb_files/1M17.pdb, erlotinib_WT
load pdb_files/2ITY.pdb, gefitinib_WT
load pdb_files/2ITZ.pdb, gefitinib_L858R
load pdb_files/6JXT.pdb, osimertinib_WT_sites
load pdb_files/6LUD.pdb, osimertinib_triple
load pdb_files/6LUB.pdb, CH7233163_triple
load pdb_files/2J6M.pdb, AEE788_WT
load pdb_files/2JIU.pdb, AEE788_T790M
load pdb_files/7ZYM.pdb, brigatinib_double
load pdb_files/7TVD.pdb, alternate_ex19del_apo
align gefitinib_L858R and chain A and name CA and resi 718-857, gefitinib_WT and chain A and name CA and resi 718-857
align osimertinib_triple and chain A and name CA and resi 718-857, osimertinib_WT_sites and chain A and name CA and resi 718-857
align CH7233163_triple and chain A and name CA and resi 718-857, osimertinib_WT_sites and chain A and name CA and resi 718-857
align AEE788_T790M and chain A and name CA and resi 718-857, AEE788_WT and chain A and name CA and resi 718-857
hide everything
show cartoon, polymer.protein
show sticks, (not erlotinib_WT and resi 790+793+797+858 and polymer.protein) or resn AQ4+IRE+YY3+EUX+AEE+6GY
show sticks, erlotinib_WT and polymer.protein and resi 766+769+773+834
color gray70, polymer.protein
color marine, (gefitinib_WT or osimertinib_WT_sites) and resn IRE+YY3
color salmon, (gefitinib_L858R or osimertinib_triple) and resn IRE+YY3
color teal, CH7233163_triple and resn EUX
set cartoon_transparency, 0.55
bg_color white
disable all
enable osimertinib_WT_sites
enable osimertinib_triple
orient (osimertinib_WT_sites or osimertinib_triple) and resn YY3
zoom (osimertinib_WT_sites or osimertinib_triple) and resn YY3, 10
