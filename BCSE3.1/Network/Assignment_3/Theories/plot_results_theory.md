# Plot Results Theory — `plot_results.py`

> **File**: `plot_results.py`  
> **Role**: Data visualization and graph generation  
> **Layer**: Analysis / Reporting

---

## 1. What This Module Does

`plot_results.py` reads `results.csv` (produced by `benchmark.py`) and generates **9 publication-quality figures** using Matplotlib. These figures directly satisfy the assignment's plotting requirements and include scope extras.

---

## 2. Figure Catalog

### Required by Assignment

| Figure | Title | X-axis | Y-axis | Data source |
|--------|-------|--------|--------|-------------|
| Fig 1 | p-Persistent: Collisions vs p | p | Collisions | p-sweep |
| Fig 2 | p-Persistent: Avg Delay vs p | p | Avg Delay | p-sweep |
| Fig 3 | p-Persistent: Throughput vs p | p | Throughput | p-sweep |
| Fig 4 | All Protocols: Collisions vs N | N | Collisions | N-sweep |
| Fig 5 | All Protocols: Avg Delay vs N | N | Avg Delay | N-sweep |
| Fig 6 | All Protocols: Throughput vs N | N | Throughput | N-sweep |

### Scope Extras

| Figure | Title | Description |
|--------|-------|-------------|
| Fig 7 | Combined 2×3 Summary | All 6 figures in one panel (for report) |
| Fig 8 | Theoretical Throughput | S vs G curves from textbook formulas |
| Fig 9 | p-Persistent Heatmap | Throughput as color for (p, N) grid |

---

## 3. Styling

Consistent styling following the Assignment 2 pattern:

```python
COLORS = {
    "non_persistent": "#E63946",   # vivid red
    "1_persistent":   "#457B9D",   # steel blue
    "p_persistent":   "#2A9D8F",   # teal
    "csma_cd":        "#F4A261",   # amber
}
```

- Top and right spines removed for clean look
- Dashed grid with 35% opacity
- High DPI (150) for crisp output
- Consistent markers per protocol (circle, square, triangle, diamond)

---

## 4. Theoretical Throughput Formulas (Fig 8)

The textbook formulas for throughput S as a function of offered load G:

### Non-Persistent CSMA
```
S = G × e^(-aG) / (G(1+2a) + e^(-aG))
```

### 1-Persistent CSMA
```
S = G(1 + G + aG(1 + G + aG/2)) × e^(-G(1+a)) /
    (G(1+2a) - (1 - e^(-aG)) + (1+aG) × e^(-G(1+a)))
```

### CSMA/CD
```
S_max ≈ 1 / (1 + 6.44a)
```

Where `a = τ / T_frame` (propagation delay / transmission time ratio).

---

## 5. Data Processing

The CSV data is processed using Pandas:
1. **Filter** by `sweep_type` (p_sweep or n_sweep)
2. **Group by** the independent variable (p or N)
3. **Aggregate** using mean (averaging over multiple runs)
4. **Plot** with Matplotlib

---

## 6. Usage

```bash
# Generate all figures (interactive display)
python3 plot_results.py

# Save only, no display
python3 plot_results.py --no-show

# Custom CSV and output directory
python3 plot_results.py --csv my_results.csv --outdir my_plots/
```

All figures are saved as PNG in the `plots/` directory.
