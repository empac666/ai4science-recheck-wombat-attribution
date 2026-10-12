"""Reproduce the two numerical feasibility probes, not the preregistered panel."""
import argparse
import pathlib
import sys
import json
import time
import torch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'repo'))
from mpnn import MoleculeHDetector, smiles_to_torch
from mpnn.molecule_o_variants import SmoothingMoleculeODetector
from xai_methods import BatchDimensionRemover
from captum.attr import IntegratedGradients

parser = argparse.ArgumentParser()
parser.add_argument('--method', choices=['gausslegendre', 'riemann_middle'], required=True)
parser.add_argument('--output', type=pathlib.Path, required=True)
args = parser.parse_args()
torch.set_num_threads(1)
rows = []
cases = [
    (MoleculeHDetector, 'NC(=O)NN=C1CCCC(C(=O)O)C1'),
    (SmoothingMoleculeODetector,
     json.loads((ROOT/'evidence/hf_pattern_12_rows.json').read_text())['rows'][0]['row']['SMILES'])
]
for cls, smiles in cases:
    model = cls().double().eval()
    x, ei, e = smiles_to_torch(smiles)
    x, e = x.double(), e.double()
    start = time.perf_counter()
    attrs, delta = IntegratedGradients(BatchDimensionRemover(model)).attribute(
        (x[None], e[None]), baselines=(torch.zeros_like(x)[None], torch.zeros_like(e)[None]),
        additional_forward_args=(ei[None],), n_steps=5000, internal_batch_size=1,
        method=args.method, return_convergence_delta=True)
    row = dict(model=cls.__name__, steps=5000, method=args.method, dtype='float64',
               seconds=time.perf_counter()-start, convergence_delta=delta.item(),
               all_finite=all(torch.isfinite(a).all().item() for a in attrs))
    rows.append(row)
    print(json.dumps(row), flush=True)
args.output.write_text(json.dumps(rows, indent=2)+'\n')
