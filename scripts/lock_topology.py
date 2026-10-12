"""Local RDKit topology整理 only; never imports models or computes attributions."""
import csv
import hashlib
import json
from pathlib import Path
from rdkit import Chem, rdBase

ROOT = Path(__file__).resolve().parents[1]
SMARTS = {
    4: '[CHD3]C(=O)O[CH2][CH2]N([CH2][CH3])[CH2][CH3]',
    5: '[CHD3]([CH2][CD3](=N[NH][CD3](=O)))C(=O)[OH]',
    12: '[!#1][CH]=O',
}
MODELS = {4: 'MoleculeGDetector', 5: 'MoleculeHDetector', 12: 'MoleculeODetector'}

def topology(smiles, pattern):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {'parse_failed': True}
    mol = Chem.RemoveAllHs(mol)
    query = Chem.MolFromSmarts(SMARTS[pattern])
    d_indices = {a.GetIdx() for a in query.GetAtoms() if 'D' in a.GetSmarts()}
    motif = set()
    for match in mol.GetSubstructMatches(query):
        motif.update(match)
        for i in d_indices:
            motif.update(a.GetIdx() for a in mol.GetAtomWithIdx(match[i]).GetNeighbors())
    return dict(canonical_smiles=Chem.MolToSmiles(mol, canonical=True),
                heavy_atoms=mol.GetNumHeavyAtoms(), bonds=mol.GetNumBonds(),
                atoms=mol.GetNumAtoms(), motif_atoms=sorted(motif), parse_failed=False)

smoke = json.loads((ROOT / 'evidence/smoke_result.json').read_text())
ids = ['S4', 'S5', 'S12', 'M5', 'N12']
seen_cases = [smoke['cases'][i] for i in [0, 1, 2, 4, 5]]
seen = [dict(id=key, input_smiles=x['smiles'], **topology(x['smiles'], x['pattern']))
        for key, x in zip(ids, seen_cases)]
excluded = {x['canonical_smiles'] for x in seen}
audits = []
candidates = {}
for readout in ['R1', 'R2']:
    for pattern, model in MODELS.items():
        relative = Path('repo/artifacts/explainability_method_tester') / readout / model / 'positive_explainability_results.csv'
        source = ROOT / relative
        rows = list(csv.DictReader(source.open()))
        totals = dict(nonblank_rows=0, parse_failed=0, outside_heavy_atom_range=0,
                      no_bonds=0, motif_class_mismatch_nonblank=0,
                      motif_class_mismatch_blank=0)
        keys = []
        for row in rows:
            nonblank = bool(row['Integrated Gradients_auroc'].strip())
            t = topology(row['SMILES'], pattern)
            if nonblank:
                totals['nonblank_rows'] += 1
                if t['parse_failed']:
                    totals['parse_failed'] += 1
                else:
                    keys.append(t['canonical_smiles'])
                    totals['outside_heavy_atom_range'] += int(not 2 <= t['heavy_atoms'] <= 100)
                    totals['no_bonds'] += int(t['bonds'] == 0)
            if t['parse_failed']:
                continue
            defined = 0 < len(t['motif_atoms']) < t['atoms']
            if defined != nonblank:
                totals['motif_class_mismatch_nonblank' if nonblank else 'motif_class_mismatch_blank'] += 1
            if readout == 'R2' and pattern == 12 and t['canonical_smiles'] not in excluded and 2 <= t['heavy_atoms'] <= 100 and t['bonds'] > 0 and defined:
                candidates[t['canonical_smiles']] = dict(canonical_smiles=t['canonical_smiles'], heavy_atoms=t['heavy_atoms'], bonds=t['bonds'])
        audits.append(dict(pattern=pattern, readout=readout, csv=str(relative),
                           csv_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                           csv_rows=len(rows), unique_nonblank_canonical_smiles=len(set(keys)), **totals))
examples = json.loads((ROOT / 'evidence/mechanism_examples.json').read_text())
mechanisms = []
for pattern, key in [(4, 'pattern4'), (5, 'pattern5')]:
    x = examples[key]
    t = topology(x['smiles'], pattern)
    mol = Chem.RemoveAllHs(Chem.MolFromSmiles(x['smiles']))
    mechanisms.append(dict(pattern=pattern, input_smiles=x['smiles'], atom_index_0based=x['atom'],
                           element=mol.GetAtomWithIdx(x['atom']).GetSymbol(),
                           nonmotif=x['atom'] not in t['motif_atoms'], **t))
conf = [candidates[k] for k in sorted(candidates)[:16]]
out = dict(version='R12-draft-3', purpose='topology-only; no forward, gradient, integration or metric evaluation',
           rdkit_version=rdBase.rdkitVersion, canonicalization='MolFromSmiles -> RemoveAllHs -> MolToSmiles(canonical=True, isomericSmiles=True); retain all fragments',
           sort='Python default Unicode code-point order, case-sensitive', seen=seen,
           csv_topology_audits=audits, mechanisms=mechanisms, conf_N=len(conf), conf=conf)
(ROOT / 'evidence/round3_topology_lock.json').write_text(json.dumps(out, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({'audits': audits, 'mechanisms': mechanisms, 'conf_N': len(conf), 'conf':conf}, ensure_ascii=False, indent=2))
