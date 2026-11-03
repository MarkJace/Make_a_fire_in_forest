"""Run with ./proj_env/bin/python main.py."""
import tkinter as tk
from tkinter import ttk

from forest import ASH, EMPTY, FIRE, TREE, Forest

BG = '#111d19'
PANEL = '#1b2b24'
TEXT = '#e4eee5'
MUTED = '#a5bcad'
COLORS = {EMPTY: '#1b2d24', TREE: '#4f995b', ASH: '#4b4742'}


class App:
    def __init__(self, root):
        self.root = root
        self.root.title('林间火光 · Forest Fire')
        self.root.geometry('1050x810')
        self.root.minsize(800, 640)
        self.root.configure(bg=BG)
        self.paused = False
        self.has_ignited = False
        self.density = tk.IntVar(value=65)
        self.speed = tk.DoubleVar(value=1)
        self.status = tk.StringVar()
        self.stats = tk.StringVar()
        self.density_label = tk.StringVar()
        self.speed_label = tk.StringVar()
        self.cell_size = 6
        self.offset = (0, 0)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TButton', padding=10, font=('', 11))

        header = tk.Frame(root, bg=BG)
        header.pack(fill='x', padx=24, pady=(20, 12))
        tk.Label(header, text='林间火光', font=('', 25, 'bold'),
                 bg=BG, fg=TEXT).pack(anchor='w')
        tk.Label(header, text='种一片森林，点一簇火，观察它的旅程。',
                 bg=BG, fg=MUTED, font=('', 11)).pack(anchor='w', pady=(6, 0))

        body = tk.Frame(root, bg=BG)
        body.pack(fill='both', expand=True, padx=24)
        controls = tk.Frame(body, bg=PANEL, width=235)
        controls.pack(side='right', fill='y', padx=(18, 0))
        controls.pack_propagate(False)
        self.canvas = tk.Canvas(body, bg=BG, highlightthickness=0)
        self.canvas.pack(side='left', fill='both', expand=True)
        self.canvas.bind('<Configure>', lambda event: self.draw_all())
        self.canvas.bind('<Button-1>', self.ignite)
        self.canvas.bind('<B1-Motion>', self.ignite)

        def label(text=None, variable=None, **kwargs):
            widget = tk.Label(controls, text=text, textvariable=variable,
                              bg=PANEL, fg=TEXT, anchor='w', justify='left', **kwargs)
            widget.pack(fill='x', padx=18, pady=(16, 4))
            return widget

        label('森林设置', font=('', 14, 'bold'))
        label(variable=self.density_label)
        self.scale(controls, self.density, 0, 100, 1,
                   lambda value: self.density_label.set(f'下一片森林密度 · {float(value):.0f}%'))
        self.density_label.set('下一片森林密度 · 65%')
        label('密度修改后，点击“新森林”生效。', font=('', 9), wraplength=200)
        label(variable=self.speed_label)
        self.scale(controls, self.speed, 0.25, 4, 0.25,
                   lambda value: self.speed_label.set(f'模拟速度 · {float(value):g}×'))
        self.speed_label.set('模拟速度 · 1×')
        self.pause_button = ttk.Button(controls, text='暂停', command=self.toggle_pause)
        self.pause_button.pack(fill='x', padx=18, pady=(22, 8))
        ttk.Button(controls, text='新森林 / 重置', command=self.reset).pack(fill='x', padx=18)
        label('森林实况', font=('', 14, 'bold'))
        label(variable=self.stats, font=('', 11))
        label('● 绿：树木\n● 橙：燃烧中\n● 灰：灰烬\n● 深绿：空地', font=('', 10))
        label('点击或拖动点火\n空格：暂停 / 继续\nR：生成新森林', font=('', 10))
        tk.Label(root, textvariable=self.status, bg=BG, fg=MUTED,
                 anchor='w', font=('', 11)).pack(fill='x', padx=24, pady=16)
        root.bind('<space>', lambda event: self.toggle_pause())
        root.bind('<Key-r>', lambda event: self.reset())
        root.bind('<Key-R>', lambda event: self.reset())
        self.reset()
        self.tick()

    @staticmethod
    def scale(parent, variable, start, end, resolution, command):
        tk.Scale(parent, variable=variable, from_=start, to=end, resolution=resolution,
                 orient='horizontal', showvalue=False, command=command,
                 bg=PANEL, fg=TEXT, troughcolor=BG, highlightthickness=0,
                 activebackground='#87bb81').pack(fill='x', padx=18)

    def color(self, index):
        state = self.forest.cells[index]
        if state == FIRE:
            return ('#ffcc67', '#ff983f', '#eb6135')[(self.forest.ages[index] + index) % 3]
        if state == TREE:
            return ('#477f50', '#55965e', '#65a168')[index % 3]
        return COLORS[state]

    def draw_all(self):
        self.canvas.delete('all')
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        side = max(1, min(width, height) - 4)
        self.cell_size = side / self.forest.size
        self.offset = ((width - side) / 2, (height - side) / 2)
        ox, oy = self.offset
        s = self.cell_size
        self.tiles = []
        for index in range(len(self.forest.cells)):
            row, col = divmod(index, self.forest.size)
            self.tiles.append(self.canvas.create_rectangle(
                ox + col*s, oy + row*s, ox + (col+1)*s, oy + (row+1)*s,
                fill=self.color(index), outline=''))

    def reset(self):
        self.forest = Forest(density=self.density.get() / 100)
        self.has_ignited = False
        self.paused = False
        self.pause_button.configure(text='暂停')
        self.draw_all()
        self.update_stats()

    def toggle_pause(self):
        self.paused = not self.paused
        self.pause_button.configure(text='继续' if self.paused else '暂停')
        self.update_stats()

    def ignite(self, event):
        ox, oy = self.offset
        col = int((event.x - ox) // self.cell_size)
        row = int((event.y - oy) // self.cell_size)
        if self.forest.ignite(row, col):
            self.has_ignited = True
            index = row * self.forest.size + col
            self.canvas.itemconfigure(self.tiles[index], fill=self.color(index))
            self.update_stats()

    def update_stats(self):
        counts = self.forest.counts()
        ratio = 100 * counts[ASH] / max(1, self.forest.initial_trees)
        self.stats.set(f'存活树木   {counts[TREE]:,}\n\n燃烧中      {counts[FIRE]:,}'
                       f'\n\n已烧毁      {counts[ASH]:,}（{ratio:.1f}%）'
                       f'\n\n模拟步数   {self.forest.steps}')
        if self.paused:
            message = '已暂停 · 仍可点击树木点火，点击“继续”开始蔓延。'
        elif counts[FIRE]:
            message = '火正在蔓延 · 可以继续点击其他树木点火。'
        elif self.has_ignited:
            message = '火已熄灭 · 可继续点燃剩余树木，或生成一片新森林。'
        elif not self.forest.initial_trees:
            message = '这里是一片空地 · 提高森林密度后，点击“新森林”。'
        else:
            message = '点击绿色树木点火 · 点击空地不会引燃。'
        self.status.set(message)

    def tick(self):
        if not self.paused and FIRE in self.forest.cells:
            for index in self.forest.step():
                self.canvas.itemconfigure(self.tiles[index], fill=self.color(index))
            self.update_stats()
        self.root.after(max(15, int(120 / self.speed.get())), self.tick)


if __name__ == '__main__':
    window = tk.Tk()
    App(window)
    window.mainloop()
