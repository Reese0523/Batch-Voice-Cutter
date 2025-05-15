import os
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from moviepy.editor import VideoFileClip, concatenate_videoclips
import whisper

# 使用 tkinter 建立 GUI
class BatchVoiceCutter(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("批次無人聲自動剪輯工具")
        self.geometry("400x200")

        tk.Label(self, text="選擇要處理的資料夾：").pack(pady=10)
        self.folder_path = tk.StringVar()
        tk.Entry(self, textvariable=self.folder_path, width=50).pack()
        tk.Button(self, text="瀏覽...", command=self.browse_folder).pack(pady=5)
        tk.Button(self, text="開始處理", command=self.start_process).pack(pady=10)

        self.model = whisper.load_model("base")  # 可改成 tiny、small 等以提速

    def browse_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.folder_path.set(path)

    def start_process(self):
        folder = self.folder_path.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("錯誤", "請選擇有效的資料夾路徑！")
            return
        threading.Thread(target=self.process_folder, args=(folder,), daemon=True).start()
        messagebox.showinfo("開始", "處理已開始，完成後會有通知。")

    def process_folder(self, folder):
        output_dir = os.path.join(folder, "output")
        os.makedirs(output_dir, exist_ok=True)

        for filename in os.listdir(folder):
            if not filename.lower().endswith(('.mp4', '.mov', '.mkv', '.avi')):
                continue
            input_path = os.path.join(folder, filename)
            try:
                self.process_video(input_path, output_dir)
            except Exception as e:
                print(f"處理 {filename} 時發生錯誤: {e}")
        messagebox.showinfo("完成", "所有影片已處理完畢！")

    def process_video(self, input_path, output_dir):
        basename = os.path.splitext(os.path.basename(input_path))[0]
        # 1. 讀取影片
        video = VideoFileClip(input_path)
        # 2. 提取音訊至暫存檔
        tmp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
        video.audio.write_audiofile(tmp_wav, logger=None)
        # 3. 使用 Whisper 辨識語音段落
        result = self.model.transcribe(tmp_wav, fp16=False)
        segments = result.get('segments', [])
        os.remove(tmp_wav)

        if not segments:
            print(f"{basename} 沒有偵測到語音，已跳過。")
            return

        # 4. 擷取有聲段落並合併
        clips = []
        for seg in segments:
            start, end = seg['start'], seg['end']
            clips.append(video.subclip(start, end))
        final = concatenate_videoclips(clips)
        # 5. 輸出影片
        output_path = os.path.join(output_dir, f"{basename}_cut.mp4")
        final.write_videofile(output_path, codec="libx264", audio_codec="aac")
        video.close()
        final.close()
        print(f"已輸出: {output_path}")

if __name__ == "__main__":
    app = BatchVoiceCutter()
    app.mainloop()  
