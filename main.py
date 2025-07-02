import os
import tkinter as tk
from tkinter import filedialog, messagebox, Scrollbar, StringVar
from PIL import Image, ImageTk

CLASS_COLORS = [
    "#E57373",
    "#64B5F6",
    "#81C784",
    "#BA68C8",
    "#4DB6AC",
    "#A1887F",
    "#90A4AE",
    "#FF8A65",
    "#4FC3F7",
    "#AED581",
    "#9575CD",
    "#F06292",
]

def load_yolo_labels(label_file):
    labels = []
    with open(label_file, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) != 5:
                continue
            cls, x, y, w, h = parts
            labels.append({'class': cls, 'x': float(x), 'y': float(y), 'w': float(w), 'h': float(h)})
    return labels


def save_yolo_labels(label_file, labels):
    with open(label_file, 'w') as f:
        for lbl in labels:
            f.write(f"{lbl['class']} {lbl['x']} {lbl['y']} {lbl['w']} {lbl['h']}\n")


class BBoxCloneApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("BBox Clone Tool")
        self.configure(bg="#f5f5f5")
        self.resizable(True, True)
        self.geometry("1000x600")

        self.img_folder = None
        self.label_folder = None
        self.images = []
        self.current = 0
        self.src_labels = []

        self.bbox_rects = []
        self.selected_rects = []

        # grid config
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(2, weight=0)

        # Canvas + scrollbars
        self.canvas = tk.Canvas(self, bg="#fff", highlightthickness=0)
        hbar = Scrollbar(self, orient=tk.HORIZONTAL, command=self.canvas.xview)
        vbar = Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.config(xscrollcommand=hbar.set, yscrollcommand=vbar.set)
        self.canvas.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)
        hbar.grid(row=1, column=0, sticky='ew', padx=5)
        vbar.grid(row=0, column=1, sticky='ns', pady=5)

        # Control panel
        ctrl = tk.Frame(self, bg="#eeeeee")
        ctrl.grid(row=0, column=2, sticky='ns', padx=5, pady=5)

        # File selectors
        tk.Button(ctrl, text="Open Images", width=20, command=self.open_folder).pack(pady=4)
        tk.Button(ctrl, text="Open Labels", width=20, command=self.open_label_folder).pack(pady=4)

        # Frame navigation
        tk.Label(ctrl, text="Frame #", bg="#eeeeee").pack(pady=(8, 0))
        self.spin_var = StringVar(value='0')
        self.source_spin = tk.Spinbox(
            ctrl, from_=0, to=0, textvariable=self.spin_var, width=5,
            command=self.on_spin_change, relief='flat'
        )
        self.source_spin.pack(pady=2)
        self.spin_var.trace_add('write', self.on_spin_change)
        nav = tk.Frame(ctrl, bg="#eeeeee")
        nav.pack(pady=4)
        tk.Button(nav, text="<", width=4, command=lambda: self.change_frame(-1)).pack(side='left', padx=2)
        tk.Button(nav, text=">", width=4, command=lambda: self.change_frame(1)).pack(side='left', padx=2)

        # Label operations
        self.listbox = tk.Listbox(ctrl, selectmode=tk.MULTIPLE, width=30, height=8)
        self.listbox.pack(pady=2)
        self.listbox.bind('<Delete>', self.delete_selection)
        self.listbox.bind('<<ListboxSelect>>', self.on_listbox_select)

        # Cloning controls
        tk.Label(ctrl, text="Clone to next", bg="#eeeeee").pack(pady=(8, 0))
        self.clone_count = tk.Entry(ctrl, width=5, relief='flat')
        self.clone_count.insert(0, "1")
        self.clone_count.pack(pady=2)
        tk.Button(ctrl, text="Clone", width=20, command=self.clone).pack(pady=6)

    def open_folder(self):
        self.img_folder = filedialog.askdirectory()
        if not self.img_folder:
            return
        self.images = sorted([f for f in os.listdir(self.img_folder)
                              if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
        if not self.images:
            messagebox.showwarning("Warning", "No images found.")
            return
        self.current = 0
        self.source_spin.config(to=len(self.images) - 1)
        self.spin_var.set('0')
        self.load_frame()

    def open_label_folder(self):
        self.label_folder = filedialog.askdirectory()
        self.load_source(self.current)
        self.load_frame()

    def on_spin_change(self, *args):
        try:
            idx = int(self.spin_var.get())
        except ValueError:
            return
        if 0 <= idx < len(self.images):
            self.current = idx
            self.load_source(self.current)

    def load_frame(self):
        img_path = os.path.join(self.img_folder, self.images[self.current])
        img = Image.open(img_path)
        self.img_w, self.img_h = img.size
        self.tkimg = ImageTk.PhotoImage(img)
        # adjust minsize
        self.update_idletasks()
        ctrl_w = 255
        self.minsize(self.img_w + ctrl_w, self.img_h + 40)
        # render
        self.canvas.config(scrollregion=(0, 0, self.img_w, self.img_h))
        self.canvas.delete('all')
        self.bbox_rects.clear()
        self.selected_rects.clear()
        self.canvas.create_image(0, 0, anchor='nw', image=self.tkimg)
        if self.label_folder:
            self.draw_boxes(self.current)

    def load_source(self, idx):
        if not (self.label_folder and self.images): return
        txt = os.path.splitext(self.images[idx])[0] + '.txt'
        path = os.path.join(self.label_folder, txt)
        self.src_labels = load_yolo_labels(path) if os.path.exists(path) else []
        self.listbox.delete(0, tk.END)
        for i, lbl in enumerate(self.src_labels):
            cls = lbl['class']
            color = CLASS_COLORS[int(cls) % len(CLASS_COLORS)]
            self.listbox.insert(tk.END, f"{i}: {cls} @ ({lbl['x']:.2f},{lbl['y']:.2f})")
            self.listbox.itemconfig(i, fg=color)
        self.load_frame()

    def change_frame(self, delta):
        if not self.images: return
        self.current = max(0, min(self.current + delta, len(self.images) - 1))
        self.load_frame()
        self.spin_var.set(str(self.current))

    def draw_boxes(self, idx):
        txt = os.path.splitext(self.images[idx])[0] + '.txt'
        path = os.path.join(self.label_folder, txt)
        if not os.path.exists(path): return

        current_sel = set(self.listbox.curselection())
        for i, lbl in enumerate(self.src_labels):
            color = 'red' if i in current_sel else CLASS_COLORS[int(lbl['class']) % len(CLASS_COLORS)]
            box_id = self._draw_box(lbl, outline=color, width=2)
            self.bbox_rects.append(box_id)

    def delete_selection(self, event=None):
        sel = list(self.listbox.curselection())
        if not sel: return
        for i in sorted(sel, reverse=True): del self.src_labels[i]
        txt = os.path.splitext(self.images[self.current])[0] + '.txt'
        path = os.path.join(self.label_folder, txt)
        save_yolo_labels(path, self.src_labels)
        self.load_source(self.current)

    def on_listbox_select(self, event=None):
        self.draw_boxes(self.current)

    def _draw_box(self, lbl, outline='green', width=2):
        x = lbl['x'] * self.img_w
        y = lbl['y'] * self.img_h
        bw = lbl['w'] * self.img_w
        bh = lbl['h'] * self.img_h
        return self.canvas.create_rectangle(x - bw / 2, y - bh / 2, x + bw / 2, y + bh / 2, outline=outline, width=width)

    def clone(self):
        try:
            frames = int(self.clone_count.get())
        except:
            messagebox.showerror("Error", "Invalid frames");return
        src_idx = self.current
        sel = self.listbox.curselection()
        if not sel: messagebox.showwarning("Warning", "No boxes");return
        for offset in range(1, frames + 1):
            tgt = src_idx + offset
            if tgt >= len(self.images): break
            txt = os.path.splitext(self.images[tgt])[0] + '.txt'
            path = os.path.join(self.label_folder, txt)
            dst = load_yolo_labels(path) if os.path.exists(path) else []
            for i in sel: dst.append(self.src_labels[i])
            save_yolo_labels(path, dst)
        messagebox.showinfo("Done", f"Cloned {len(sel)} boxes.")


if __name__ == '__main__':
    app = BBoxCloneApp()
    app.mainloop()
