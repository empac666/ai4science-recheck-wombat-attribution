"""CPU feasibility only; no cohort selection or formal pressure grid."""
import time
WALL_START = time.perf_counter()
import os
os.environ.setdefault('MPLBACKEND', 'Agg')
import sys
import json
import pathlib
import platform
import importlib.metadata
import resource
import numpy as np
import torch
from rdkit import Chem
from sklearn.metrics import roc_auc_score

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'repo'))
from mpnn import MoleculeGDetector, MoleculeHDetector, MoleculeODetector, mol_to_torch
from mpnn.molecule_o_variants import SmoothingMoleculeODetector
from xai_methods import IGAttributionMethod, BatchDimensionRemover
from captum.attr import IntegratedGradients
from highlight_smarts import highlight_atoms_in_mol
from krfp_models import name_to_post_smarts

torch.set_num_threads(1)
torch.manual_seed(2026101101)
IMPORT_SECONDS = time.perf_counter() - WALL_START
records = []
classes = [(4, MoleculeGDetector), (5, MoleculeHDetector), (12, MoleculeODetector), (12, SmoothingMoleculeODetector)]

def run_case(pattern, cls, smiles, origin, expected):
    start = time.perf_counter()
    model = cls().cpu().eval()
    mol = Chem.RemoveAllHs(Chem.MolFromSmiles(smiles))
    x, ei, e = mol_to_torch(mol)
    with torch.no_grad():
        pred = model(x, e, ei).item()
        baseline = model(torch.zeros_like(x), torch.zeros_like(e), ei).item()
    assert (pred > 0.5) == expected, (cls.__name__, smiles, pred)
    assert abs(baseline) <= 1e-6
    smarts = name_to_post_smarts['MoleculeODetector' if pattern == 12 else cls.__name__]
    explainer = IGAttributionMethod(model, smarts, [], [])
    t = time.perf_counter()
    a, ae = explainer.explain(x, e, ei)
    ig_seconds = time.perf_counter() - t
    assert torch.isfinite(a).all() and torch.isfinite(ae).all()
    y = np.array([i in highlight_atoms_in_mol(mol, smarts) for i in range(mol.GetNumAtoms())])
    scores = a.abs().sum(dim=1).detach().numpy()
    signed_sum = (a.sum() + ae.sum()).item()
    row = dict(pattern=pattern, model=cls.__name__, source=origin, smiles=smiles,
               atoms=mol.GetNumAtoms(), directed_edges=ei.shape[1], prediction=pred,
               zero_baseline=baseline, ig_steps=50, ig_method='gausslegendre',
               ig_seconds=ig_seconds, attribution_finite=True,
               auroc=float(roc_auc_score(y, scores)) if y.any() and (~y).any() else None,
               signed_completeness_residual=signed_sum-(pred-baseline),
               node_attribution=scores.tolist(), seconds=time.perf_counter()-start)
    records.append(row)
    print(json.dumps({k:v for k,v in row.items() if k not in ('smiles','node_attribution')}), flush=True)
    return model, x, ei, e

timings = []
COMPUTE_START = time.perf_counter()
for pattern, cls in classes:
    d = json.loads((ROOT/'evidence'/f'hf_pattern_{pattern}_rows.json').read_text())
    entry = d['rows'][0]['row']
    model, x, ei, e = run_case(pattern, cls, entry['SMILES'], 'HF viewer first row (not random)', True)
    t = time.perf_counter()
    attrs, delta = IntegratedGradients(BatchDimensionRemover(model)).attribute(
        inputs=(x[None], e[None]), baselines=(torch.zeros_like(x)[None],torch.zeros_like(e)[None]),
        additional_forward_args=(ei[None],), n_steps=200, method='gausslegendre',
        internal_batch_size=1, return_convergence_delta=True)
    assert all(torch.isfinite(a).all() for a in attrs) and torch.isfinite(delta).all()
    timings.append(dict(model=cls.__name__, atoms=x.shape[0], steps=200,
                        seconds=time.perf_counter()-t, convergence_delta=delta.item()))

run_case(5, MoleculeHDetector, 'NC(=O)NN=C1CCCC(C(=O)O)C1', 'published notebook example', True)
for cls in (MoleculeODetector, SmoothingMoleculeODetector):
    run_case(12, cls, 'CC(=O)C', 'synthetic negative for interface check', False)

out = dict(status='PASS', purpose='feasibility only', device='cpu', torch_threads=1,
           python=platform.python_version(), packages={n:importlib.metadata.version(n) for n in
           ['torch','torch-geometric','captum','rdkit','numpy','pandas','matplotlib','scikit-learn','pymupdf','pyarrow']},
           import_seconds=IMPORT_SECONDS, compute_seconds=time.perf_counter()-COMPUTE_START,
           process_wall_seconds=time.perf_counter()-WALL_START,
           peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
           cases=records, calibration_200_steps=timings)
(ROOT/'evidence'/'smoke_result.json').write_text(json.dumps(out, indent=2, ensure_ascii=False)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in ('packages','cases')}, ensure_ascii=False), flush=True)
