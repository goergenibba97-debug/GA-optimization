"""Creates input_template.xlsx (random but feasible example instance)."""
import numpy as np
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.comments import Comment

rng = np.random.default_rng(7)
K, I, J = 10, 7, 15
R = rng.integers(40, 120, J)
O = rng.integers(int(R.sum() / K * 1.5), int(R.sum() / K * 2.2), K)
Cap = rng.integers(int(R.sum() / 3.2), int(R.sum() / 2.2), I)
F = rng.integers(2000, 6000, I)
C = rng.integers(2, 15, (K, I)); D = rng.integers(3, 20, (I, J))

wb = Workbook(); wb.remove(wb.active)
HEAD = PatternFill("solid", fgColor="1F3A5F"); INP = Font(name="Arial", color="0000FF")
def sheet(name, header, rows, note):
    ws = wb.create_sheet(name); ws.append(header)
    for r in rows: ws.append([v.item() if hasattr(v, "item") else v for v in r])
    for c in ws[1]:
        c.font = Font(name="Arial", bold=True, color="FFFFFF"); c.fill = HEAD
        c.alignment = Alignment(horizontal="center")
    for row in ws.iter_rows(min_row=2):
        for c in row: c.font = INP if c.column > 1 or name.startswith("Cost") and c.column > 1 else Font(name="Arial", bold=True)
    ws.column_dimensions["A"].width = 16
    for col in "BCDEFGHIJKLMNOP": ws.column_dimensions[col].width = 12
    ws["A1"].comment = Comment(note, "Template")
    ws.freeze_panes = "B2"
sheet("Suppliers", ["Supplier", "Supply O_k"], [[f"S{k+1}", O[k]] for k in range(K)],
      "Edit blue cells. One row per supplier. Add/remove rows freely.")
sheet("Customers", ["Customer", "Demand R_j"], [[f"C{j+1}", R[j]] for j in range(J)],
      "Edit blue cells. One row per customer.")
sheet("Warehouses", ["Warehouse", "Fixed cost F_i", "Capacity Cap_i"],
      [[f"W{i+1}", F[i], Cap[i]] for i in range(I)], "Edit blue cells. One row per candidate warehouse.")
sheet("Cost_Supplier_Warehouse", ["Supplier \\ Warehouse"] + [f"W{i+1}" for i in range(I)],
      [[f"S{k+1}", *C[k]] for k in range(K)], "Unit transport cost C_ki. Rows = suppliers, columns = warehouses (same order as the other sheets).")
sheet("Cost_Warehouse_Customer", ["Warehouse \\ Customer"] + [f"C{j+1}" for j in range(J)],
      [[f"W{i+1}", *D[i]] for i in range(I)], "Unit transport cost D_ij. Rows = warehouses, columns = customers.")
ws = wb.create_sheet("README", 0)
for line in ["Warehouse Location - input template", "",
             "1. Edit only the blue cells (example values are pre-filled).",
             "2. Keep sheet names and the order of suppliers / warehouses / customers consistent.",
             "3. Matrix sheets must be (#suppliers x #warehouses) and (#warehouses x #customers).",
             "4. Feasibility: total supply >= total demand and total warehouse capacity >= total demand.",
             "5. Upload the file in the web app and press 'Run genetic algorithm'.",
             "Data are randomly generated placeholders (seed 7), not real figures."]:
    ws.append([line])
ws["A1"].font = Font(name="Arial", bold=True, size=14); ws.column_dimensions["A"].width = 90
wb.save("input_template.xlsx")
