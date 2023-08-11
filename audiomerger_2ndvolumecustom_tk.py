import tkinter as tk
from tkinter import ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
import os
import subprocess
import threading
import numpy as np
import datetime

ffmpegpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg.exe")
# print(ffmpegpath)
path = ""
isprocessing = False
temppaths = []
loudestsegments_dict = dict()

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
    threadinfo.configure(text="")
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
                previewbutton.configure(state="normal")
            else:
                path_label.config(text=f"Selekted file is not MKV/MP4:\n{path}")
                combinebutton.configure(state="disabled")
                previewbutton.configure(state="normal")

def run_command(commandtorun):
    if os.path.exists(ffmpegpath):
        
        start_thread(commandtorun)
        start_loading_animation()
        # cmd = f'"{ffmpegpath}" -i "{path}" -c:v copy -filter_complex "[0:1]volume=1.0[a];[0:2]volume={volume}[b];[a][b]amerge=inputs=2" -movflags faststart -threads {threadsslider.get()} -y "{mergedpath}"'
        # subprocess.run(cmd, shell=True)

    else:
        threadinfo.configure(text="ffmpeg isn't found on this script's directory.")
        print("ffmpeg isn't found on this script's directory.")
    # cmd_process = subprocess.Popen(["cmd", "/c", "start cmd /c echo a && start cmd /c timeout /t 5 && start cmd /k echo b"])

def run_ffmpeg(commandtorun):

    def samples_to_time(samples, sample_rate=44100):
        total_seconds = samples / sample_rate
        time = datetime.timedelta(seconds=total_seconds)
        return str(time)

    def hms_to_seconds(hms):
        h, m, s = map(int, hms.split(':'))
        total_seconds = h * 3600 + m * 60 + s
        return total_seconds

    def runifnopathyet(cmd, pathtocheck=None):
        if pathtocheck:
            if os.path.exists(pathtocheck):
                return
        subprocess.run(cmd, shell=True)
        
    global isprocessing
    global canvas
    combinebutton.config(state=tk.DISABLED)
    previewbutton.config(state=tk.DISABLED)
    isprocessing = True
    canvas.pack(side=tk.LEFT)
    
    volumeslider.configure(state="disabled")
    filedir = os.path.dirname(path)
    barefilename, ext = os.path.splitext(os.path.basename(path))
    
    volume = volumeslider.get()
    if 1 <= volume <= 100:
        volume = round(volume / 100, 2)
    if not volume:
            volume = 1.0
         
    if commandtorun == "combine":
        mergedpath = os.path.join(filedir, barefilename + "_merged" + ".mp4")
        threadinfo.configure(text="Merging the audio track with chosen volume...")
        cmd = f'"{ffmpegpath}" -i "{path}" -c:v copy -filter_complex "[0:1]volume=1.0[a];[0:2]volume={volume}[b];[a][b]amerge=inputs=2" -movflags faststart -threads {threadsslider.get()} -y "{mergedpath}"'
        subprocess.run(cmd, shell=True)
        threadinfo.configure(text="Audio merged.")
        
    elif commandtorun == "preview":
        m4apath_1 = os.path.join(filedir, barefilename + "_1sttrackaudio" + ".m4a")
        m4apath_2 = os.path.join(filedir, barefilename + "_2ndtrackaudio" + ".m4a")
        
        cmd = f'"{ffmpegpath}" -hide_banner -i "{path}" -map 0:a:0 -vn -acodec copy -threads {threadsslider.get()} "{m4apath_1}" -y'
        threadinfo.configure(text="Extracting first audio track...")
        runifnopathyet(cmd, m4apath_1)
        cmd = f'"{ffmpegpath}" -hide_banner -i "{path}" -map 0:a:1 -vn -acodec copy -threads {threadsslider.get()} "{m4apath_2}" -y'
        threadinfo.configure(text="Extracting second audio track...")
        runifnopathyet(cmd, m4apath_2)
        
        if not path in loudestsegments_dict:
            threadinfo.configure(text="Analyzing the loudest part of the 2nd track...")
            command = [
                r"H:\ffmpeg", "-hide_banner", "-i", m4apath_2,
                "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "1",
                "-f", "s16le", "-"
            ]
            audio_data = subprocess.check_output(command, stderr=subprocess.PIPE)

            # Convert the raw audio data to a numpy array
            samples = np.frombuffer(audio_data, dtype=np.int16)
            
            split_interval=10
            
            # Calculate the number of samples per split interval
            samples_per_split = int(split_interval * 44100)  # Assuming a sample rate of 44100 Hz

            # Split the audio into segments every split_interval seconds
            num_splits = len(samples) // samples_per_split
            loudest_segment = None
            loudest_amplitude = 0

            for i in range(num_splits):
                segment_start = i * samples_per_split
                segment_end = (i + 1) * samples_per_split
                segment_samples = samples[segment_start:segment_end]
                segment_amplitude = np.max(np.abs(segment_samples))

                if segment_amplitude > loudest_amplitude:
                    loudest_amplitude = segment_amplitude
                    loudest_segment = (segment_start, segment_end)
                    
            if loudest_segment:
                loudest_start_time = samples_to_time(loudest_segment[0])
                loudest_end_time = samples_to_time(loudest_segment[1])

                loudestsegments_dict[path] = (loudest_start_time, loudest_end_time)
                
        if path in loudestsegments_dict:
            print("Loudest segment start:", loudestsegments_dict[path][0])
            print("Loudest segment end:", loudestsegments_dict[path][1])

        # combinedpath = os.path.join(filedir, barefilename + "_combined" + ".m4a")
        loudestpath = os.path.join(filedir, barefilename + "_loudest" + ".m4a")
        # cmd = f'"{ffmpegpath}" -hide_banner "[1:a]volume={volume}[a1];[0:a]atrim=start={hms_to_seconds(loudestsegments_dict[path][0])}:end={hms_to_seconds(loudestsegments_dict[path][1])}[a0];[a1]atrim=start={hms_to_seconds(loudestsegments_dict[path][0])}:end={hms_to_seconds(loudestsegments_dict[path][1])}[a1];[a0][a1]amix=inputs=2:duration=longest[out]" -map "[out]" -threads {threadsslider.get()} "{loudestpath}" -y'
        startsecondstamp = hms_to_seconds(loudestsegments_dict[path][0])
        endsecondstamp = hms_to_seconds(loudestsegments_dict[path][1])

        cmd = f'"{ffmpegpath}" -i "{m4apath_1}" -i "{m4apath_2}" -hide_banner -filter_complex "[1:a]volume={volume}[a1];[0:a]atrim=start={startsecondstamp}:end={endsecondstamp}[a0];[a1]atrim=start={startsecondstamp}:end={endsecondstamp}[a1];[a0][a1]amix=inputs=2:duration=longest[out]" -map "[out]" -threads {threadsslider.get()} -write_xing 0 "{loudestpath}" -y'
        threadinfo.configure(text="Making the preview with combined audio...")
        subprocess.run(cmd, shell=True)

        # loudestpath = os.path.join(filedir, barefilename + "_loudest" + ".m4a")
        # cmd = f'"{ffmpegpath}" -hide_banner -i "{combinedpath}" -ss {loudestsegments_dict[path][0]} -to {loudestsegments_dict[path][1]} -c copy -threads {threadsslider.get()} "{loudestpath}" -y'
        # subprocess.run(cmd, shell=True)
        
        subprocess.Popen(["start", "", loudestpath], shell=True)
        
        if path in loudestsegments_dict:
            print(f"Current preview volume: {volume}")
            print("Loudest segment start:", loudestsegments_dict[path][0])
            print("Loudest segment end:", loudestsegments_dict[path][1])

        global temppaths
        for tempfile in (m4apath_1, m4apath_2, loudestpath):
            if os.path.exists(tempfile):
                temppaths.append(tempfile)
        threadinfo.configure(text="Loudest audio preview was made.")
    
    volumeslider.configure(state="normal")
    
    
    stop_loading_animation()
    canvas.pack_forget()
    isprocessing = False
    combinebutton.config(state=tk.NORMAL)
    previewbutton.config(state=tk.NORMAL)

def start_thread(commandtorun):
    global ffmpeg_thread
    ffmpeg_thread = threading.Thread(target=lambda: run_ffmpeg(commandtorun))
    ffmpeg_thread.start()

def stop_thread():
    if hasattr(start_thread, 'ffmpeg_thread') and start_thread.ffmpeg_thread.is_alive():
        start_thread.ffmpeg_thread.terminate()  # Terminate the thread immediately
    root.destroy()

def on_closing():
    for tempfile in temppaths:
       if os.path.exists(tempfile):
           os.remove(tempfile)
    stop_thread()

root = TkinterDnD.Tk()
root.title("AudioMerger_2ndTrackVolume")
window_width = 430
window_height = 560
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

previewbutton = ttk.Button(buttonframe, text="Preview Current Volume", command=lambda: run_command("preview"), state="disabled")
previewbutton.pack(side=tk.LEFT)

combinebutton = ttk.Button(buttonframe, text="Merge Audio", command=lambda: run_command("combine"), state="disabled")
combinebutton.pack(side=tk.LEFT)

canvas = tk.Canvas(buttonframe, width=40, height=40)

threadinfo = ttk.Label(root, text="")
threadinfo.pack()

# Configure drag-and-drop events for the free space
free_space.drop_target_register(DND_FILES)
free_space.dnd_bind('<<Drop>>', on_drop)

root.mainloop()
