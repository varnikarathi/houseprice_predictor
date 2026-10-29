"""
generate_architecture_diagram.py - Generates system architecture diagram for report and presentation.
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches

os.makedirs("reports/figures", exist_ok=True)

fig, ax = plt.subplots(figsize=(12, 6), dpi=300)
ax.set_xlim(0, 12)
ax.set_ylim(0, 6)
ax.axis('off')

# Background styling
fig.patch.set_facecolor('#ffffff')

# Colors
c_data = '#e0f2fe'
c_model = '#dcfce7'
c_api = '#fef3c7'
c_db = '#fae8ff'
c_ui = '#f1f5f9'
c_border = '#334155'

# Helper for drawing rounded boxes
def draw_box(x, y, w, h, title, subtitle, color, ax):
    box = patches.FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.1,rounding_size=0.15",
        facecolor=color, edgecolor='#475569', linewidth=1.5
    )
    ax.add_patch(box)
    ax.text(x + w/2, y + h*0.65, title, ha='center', va='center', fontsize=11, fontweight='bold', color='#0f172a')
    ax.text(x + w/2, y + h*0.35, subtitle, ha='center', va='center', fontsize=8.5, color='#334155', multialignment='center')

# Draw Components
# 1. Ingestion / Data
draw_box(0.5, 3.5, 2.2, 1.8, "1. Data Pipeline", "King County Sales\n(21,613 records)\nClean & Deduplicate", c_data, ax)

# 2. ML Engine / Artifacts
draw_box(3.4, 3.5, 2.4, 1.8, "2. ML Training", "Random Forest Regressor\n5-Fold CV + Tuning\nlog1p Target (Zero Leakage)", c_model, ax)

# 3. Model Storage
draw_box(3.4, 0.8, 2.4, 1.6, "Production Pipeline", "Joblib Serialization\n(models/best_model.joblib)\nMetadata & Schemas", '#f8fafc', ax)

# 4. API Backend
draw_box(6.5, 3.5, 2.3, 1.8, "3. FastAPI Service", "Pydantic Validation\nPOST /predict\nGET /metrics & /health", c_api, ax)

# 5. Database
draw_box(6.5, 0.8, 2.3, 1.6, "4. MongoDB Atlas / Local", "house_price_db\n'properties' collection\n'predictions' collection", c_db, ax)

# 6. Web UI
draw_box(9.5, 3.5, 2.0, 1.8, "5. Web Dashboard", "Single-Page HTML/JS\n5 Feature Input Groups\nAudit Log Feed", c_ui, ax)

# Draw connecting arrows
arrow_props = dict(arrowstyle="->", color='#0284c7', lw=2.2, mutation_scale=18)
arrow_props_db = dict(arrowstyle="->", color='#9333ea', lw=2.2, mutation_scale=18)
arrow_props_model = dict(arrowstyle="->", color='#16a34a', lw=2.2, mutation_scale=18)

# 1 -> 2
ax.annotate("", xy=(3.4, 4.4), xytext=(2.7, 4.4), arrowprops=arrow_props)
# 2 -> 3
ax.annotate("", xy=(4.6, 2.4), xytext=(4.6, 3.5), arrowprops=arrow_props_model)
# 3 -> 4
ax.annotate("", xy=(6.5, 4.0), xytext=(5.8, 1.6), arrowprops=dict(arrowstyle="->", color='#16a34a', lw=2, mutation_scale=16, connectionstyle="arc3,rad=-0.15"))
# 4 -> 5
ax.annotate("", xy=(7.65, 2.4), xytext=(7.65, 3.5), arrowprops=arrow_props_db)
# 6 <-> 4
ax.annotate("", xy=(8.8, 4.4), xytext=(9.5, 4.4), arrowprops=dict(arrowstyle="<->", color='#ea580c', lw=2.2, mutation_scale=18))

# Titles & legend
ax.text(6.0, 5.7, "Figure 11: End-to-End System Architecture (Data -> ML -> FastAPI -> MongoDB -> UI)", ha='center', va='center', fontsize=13, fontweight='bold', color='#0f172a')

plt.tight_layout()
out_path = "reports/figures/system_architecture.png"
fig.savefig(out_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
plt.close(fig)
print(f"Generated {out_path}")
