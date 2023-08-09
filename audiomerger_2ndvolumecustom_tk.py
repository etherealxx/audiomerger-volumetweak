import tkinter as tk
from tkinter import ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
import os
import subprocess
import threading

ffmpegpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg.exe")
print(ffmpegpath)
path = ""
isprocessing = False

import tkinter as tk

class LoadingAnimation:
    def __init__(self, canvas, x, y, radius=10, speed=15):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.radius = radius
        self.speed = speed
        self.angle = 0
        self.arc_id = None

    def start_loading(self):
        self.arc_id = self.draw_loading()

    def stop_loading(self):
        if self.arc_id:
            self.canvas.delete(self.arc_id)
            self.arc_id = None

    def draw_loading(self):
        self.canvas.delete("loading")
        self.canvas.delete("circle")
        x0 = self.x - self.radius
        y0 = self.y - self.radius
        x1 = self.x + self.radius
        y1 = self.y + self.radius
        
        self.canvas.create_oval(x0, y0, x1, y1, outline="gray", width=1, tags="circle")
        
        arc = self.canvas.create_arc(x0, y0, x1, y1, start=self.angle, extent=45, fill="green", outline="", tags="loading")
        self.angle = (self.angle + 10) % 360
        self.canvas.after(self.speed, self.draw_loading)
        return arc

def start_loading_animation(destroyafter=None):
    global loading_animation

    loading_animation = LoadingAnimation(canvas, 20, 20)
    loading_animation.start_loading()

    if destroyafter:
        root.after(destroyafter, stop_loading_animation)

def stop_loading_animation():
    global loading_animation
    loading_animation.stop_loading()
    # loading_animation.canvas.destroy()

def on_drop(event):
    global path
    if not isprocessing:
        path = event.data
        if path:
            path = os.path.normpath(path.lstrip("{").rstrip("}"))
            if path.endswith(".mp4") or path.endswith(".mkv"):
                if os.path.exists(ffmpegpath):
                    audiotrackscount = subprocess.getoutput(f'"{ffmpegpath}" -i "{path}" 2>&1 | find /c /i "audio"')
                    path_label.config(text=f"Video path:\n{path}\n(The video contains {audiotrackscount} audio tracks)")
                else:
                    path_label.config(text=f"Video path:\n{path}")
                combinebutton.configure(state="normal")
            else:
                path_label.config(text=f"Selekted file is not MKV/MP4:\n{path}")
                combinebutton.configure(state="disabled")

def run_command():
    if os.path.exists(ffmpegpath):
        
        start_thread()
        start_loading_animation()
        # cmd = f'"{ffmpegpath}" -i "{path}" -c:v copy -filter_complex "[0:1]volume=1.0[a];[0:2]volume={volume}[b];[a][b]amerge=inputs=2" -movflags faststart -threads {threadsslider.get()} -y "{mergedpath}"'
        # subprocess.run(cmd, shell=True)

    else:
        print("ffmpeg wasn't found.")
    # cmd_process = subprocess.Popen(["cmd", "/c", "start cmd /c echo a && start cmd /c timeout /t 5 && start cmd /k echo b"])

def run_ffmpeg():
    global isprocessing
    global canvas
    combinebutton.config(state=tk.DISABLED)
    isprocessing = True
    canvas.pack(side=tk.LEFT)
    
    filedir = os.path.dirname(path)
    barefilename, ext = os.path.splitext(os.path.basename(path))
    mergedpath = os.path.join(filedir, barefilename + "_merged" + ".mp4")
    
    volume = volumeslider.get()
    if 1 <= volume <= 100:
        volume = round(volume / 100, 2)
    if not volume:
            volume = 1.0

    cmd = f'"{ffmpegpath}" -i "{path}" -c:v copy -filter_complex "[0:1]volume=1.0[a];[0:2]volume={volume}[b];[a][b]amerge=inputs=2" -movflags faststart -threads {threadsslider.get()} -y "{mergedpath}"'
    subprocess.run(cmd, shell=True)
    
    stop_loading_animation()
    canvas.pack_forget()
    isprocessing = False
    combinebutton.config(state=tk.NORMAL)

def start_thread():
    global ffmpeg_thread
    ffmpeg_thread = threading.Thread(target=run_ffmpeg)
    ffmpeg_thread.start()

def stop_thread():
    if hasattr(start_thread, 'ffmpeg_thread') and start_thread.ffmpeg_thread.is_alive():
        start_thread.ffmpeg_thread.terminate()  # Terminate the thread immediately
    root.destroy()

def on_closing():
    stop_thread()

root = TkinterDnD.Tk()
root.title("AudioMerger_2ndVolumeCustom")
window_width = 430
window_height = 540
root.geometry(f"{window_width}x{window_height}")
root.protocol("WM_DELETE_WINDOW", on_closing)

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

x_coordinate = (screen_width - window_width) // 2
y_coordinate = int((screen_height - window_height) // 2)
root.geometry(f"+{x_coordinate}+{y_coordinate}")

# Create the free space (center of the window)
free_space = tk.Frame(root, bg="lightgray", width=350, height=250)
free_space.pack_propagate(0)
free_space.pack(padx=20, pady=20)

# Create a label to display the dropped file path
path_label = tk.Label(root, text="Drag and drop a MKV/MP4 file to the box above", bg="white", wraplength=460)
path_label.pack(pady=(0, 20))

sliderframe1 = ttk.Frame(root)
sliderframe1.pack()

volumelabel = ttk.Label(sliderframe1, text="2nd Audio\nTrack Volume:")
volumelabel.pack(side=tk.LEFT)

volumeslider = tk.Scale(sliderframe1, from_=0, to=100, orient="horizontal", resolution=5)
volumeslider.set(50)
volumeslider.pack(side=tk.LEFT)

sliderframe2 = ttk.Frame(root)
sliderframe2.pack()

threadslabel = ttk.Label(sliderframe2, text="Threads:")
threadslabel.pack(side=tk.LEFT)

threadsslider = tk.Scale(sliderframe2, from_=1, to=os.cpu_count(), orient="horizontal", resolution=1)
threadsslider.set(os.cpu_count())
threadsslider.pack(side=tk.LEFT)

ttk.Separator(root, orient="horizontal").pack(fill="x", pady=10, padx=20)

buttonframe = ttk.Frame(root)
buttonframe.pack()

combinebutton = ttk.Button(buttonframe, text="Merge Audio", command=run_command, state="disabled")
combinebutton.pack(side=tk.LEFT)

canvas = tk.Canvas(buttonframe, width=40, height=40)

# Configure drag-and-drop events for the free space
free_space.drop_target_register(DND_FILES)
free_space.dnd_bind('<<Drop>>', on_drop)

root.mainloop()
