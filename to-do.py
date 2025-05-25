import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import messagebox, simpledialog, ttk
import threading
import time
import os
import json
import pygame
import datetime

# Constants and files
TASKS_FILE = "tasks_with_reminders.txt"
SETTINGS_FILE = "todo_settings.json"
DEFAULT_SOUND = "reminder.wav"
THEMES = ["superhero", "solar", "flatly", "darkly", "minty", "cosmo", "cyborg"]


class ReminderApp:
    def __init__(self, root):
        self.root = root
        self.note_name = "untitled note"
        self.tasks = []
        self.selection_mode = False
        self.selected_tasks = set()

        # Name bar above left frame
        self.name_frame = tb.Frame(root)
        self.name_frame.pack(fill=tk.X, pady=5)
        self.name_label = tb.Label(self.name_frame, text=self.note_name, font=("Segoe UI", 12, "bold"))
        self.name_label.pack(side=tk.LEFT, padx=10)
        self.name_label.bind("<Button-3>", self.rename_note_prompt)

        # Main container frame
        self.main_frame = tb.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Left frame for tasks
        self.left_frame = tb.Frame(self.main_frame)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        # Search bar
        self.search_var = tk.StringVar()
        self.search_label = tb.Label(self.left_frame, text="Search Tasks:")
        self.search_label.pack()
        self.search_entry = tb.Entry(self.left_frame, textvariable=self.search_var)
        self.search_entry.pack(fill=tk.X, pady=(0, 5))
        self.search_var.trace_add("write", lambda *args: self.render_tasks())

        # Task canvas and scrollbar
        self.task_canvas = tk.Canvas(self.left_frame, width=300, height=400)
        self.task_scrollbar = tb.Scrollbar(self.left_frame, command=self.task_canvas.yview)
        self.task_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.task_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.task_canvas.configure(yscrollcommand=self.task_scrollbar.set)

        self.task_frame = tb.Frame(self.task_canvas)
        self.task_canvas.create_window((0, 0), window=self.task_frame, anchor="nw")
        self.task_frame.bind("<Configure>", lambda e: self.task_canvas.configure(scrollregion=self.task_canvas.bbox("all")))

        # Right frame
        self.right_frame = tb.Frame(self.main_frame)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)

        # Task input
        self.task_label = tb.Label(self.right_frame, text="Task Description:")
        self.task_label.pack()
        self.task_var = tk.StringVar()
        self.task_entry = tb.Entry(self.right_frame, textvariable=self.task_var, width=30)
        self.task_entry.pack(pady=5)

        self.time_label = tb.Label(self.right_frame, text="Reminder Time (HH:MM):")
        self.time_label.pack()
        self.time_var = tk.StringVar()
        self.time_entry = tb.Entry(self.right_frame, textvariable=self.time_var, width=30)
        self.time_entry.pack(pady=5)

        self.add_button = tb.Button(self.right_frame, text="Add Task", command=self.add_task)
        self.add_button.pack(pady=5)

        self.recurring_label = tb.Label(self.right_frame, text="Recurring:")
        self.recurring_label.pack()
        self.recurring_var = tk.StringVar(value="None")
        recurring_options = ["None", "Daily", "Weekly", "Monthly"]
        self.recurring_menu = ttk.OptionMenu(self.right_frame, self.recurring_var, self.recurring_var.get(), *recurring_options)
        self.recurring_menu.pack(pady=5)

        self.delete_btn = tb.Button(self.right_frame, text="Delete Task", command=self.delete_selected_task)
        self.delete_btn.pack_forget()

        self.delete_selected_btn = tb.Button(self.left_frame, text="Delete Selected", bootstyle="danger", command=self.delete_selected_tasks)
        self.cancel_selection_btn = tb.Button(self.left_frame, text="Cancel", bootstyle="secondary", command=self.exit_selection_mode)

        self.render_tasks()
        threading.Thread(target=self.check_reminders, daemon=True).start()

    def rename_note_prompt(self, event=None):
        new_name = simpledialog.askstring("Rename Note", "Enter new note name:", initialvalue=self.note_name)
        if new_name:
            self.note_name = new_name
            self.name_label.config(text=new_name)
            self.save_current_note()

    def add_task(self):
        task_text = self.task_entry.get().strip()
        task_time = self.time_var.get().strip()
        recurring = self.recurring_var.get()

        try:
            time.strptime(task_time, "%H:%M")
        except ValueError:
            messagebox.showerror("Invalid Time", "Please enter time in HH:MM format.")
            return

        if task_text and task_time:
            new_task = {
                "task": task_text,
                "time": task_time,
                "recurring": recurring,
                "completed": False
            }
            self.tasks.append(new_task)
            self.task_entry.delete(0, tk.END)
            self.time_var.set("")
            self.recurring_var.set("None")
            self.render_tasks()
            self.save_current_note()

    def render_tasks(self):
        for widget in self.task_frame.winfo_children():
            widget.destroy()

        self.task_check_vars = []
        search_query = self.search_var.get().lower().strip()

        for i, task in enumerate(self.tasks):
            text_to_check = f'{task["time"]} {task["task"]} {task.get("recurring", "")}'.lower()
            if search_query and search_query not in text_to_check:
                continue

            frame = tb.Frame(self.task_frame, bootstyle="dark")
            frame.pack(fill=tk.X, padx=5, pady=5)

            check_var = tk.BooleanVar()
            self.task_check_vars.append(check_var)

            cb = tb.Checkbutton(frame, variable=check_var)
            cb.pack(side=tk.LEFT, padx=5)
            cb.pack_forget()

            rec = task.get("recurring", "None")
            text = f'{task["time"]} - {task["task"]} ({rec})' if rec != "None" else f'{task["time"]} - {task["task"]}'

            label = tb.Label(frame, text=text, font=("Segoe UI", 11))
            label.pack(side=tk.LEFT, fill=tk.X, expand=True)

            label.bind("<Button-1>", lambda e, idx=i: self.on_task_click(idx))
            label.bind("<Button-3>", lambda e, idx=i: self.enter_selection_mode(idx))

    def on_task_click(self, index):
        if self.selection_mode:
            var = self.task_check_vars[index]
            var.set(not var.get())
        else:
            task = self.tasks[index]
            self.task_var.set(task["task"])
            self.time_var.set(task["time"])
            self.recurring_var.set(task.get("recurring", "None"))

    def enter_selection_mode(self, index):
        if not self.selection_mode:
            self.selection_mode = True
            for cb_var, frame in zip(self.task_check_vars, self.task_frame.winfo_children()):
                cb = frame.winfo_children()[0]
                cb.pack(side=tk.LEFT, padx=5)
        self.task_check_vars[index].set(True)
        self.delete_selected_btn.pack(pady=10, fill=tk.X)
        self.cancel_selection_btn.pack(pady=5, fill=tk.X)
        self.delete_btn.pack_forget()

    def toggle_task_completion(self, index):
        self.tasks[index]["completed"] = not self.tasks[index]["completed"]
        self.render_tasks()
        self.save_current_note()

    def exit_selection_mode(self):
        self.selection_mode = False
        for frame in self.task_frame.winfo_children():
            cb = frame.winfo_children()[0]
            cb.pack_forget()
        for var in self.task_check_vars:
            var.set(False)
        self.delete_selected_btn.pack_forget()
        self.cancel_selection_btn.pack_forget()
        self.delete_btn.pack(pady=10, fill=tk.X)

    def delete_selected_task(self):
        selected_indices = [i for i, var in enumerate(self.task_check_vars) if var.get()]
        if selected_indices:
            self.tasks = [t for i, t in enumerate(self.tasks) if i not in selected_indices]
            self.render_tasks()
            self.save_current_note()

    def delete_selected_tasks(self):
        self.delete_selected_task()

    def check_reminders(self):
        while True:
            now_time = time.strftime("%H:%M")
            today_date = datetime.date.today()

            for i, task in enumerate(self.tasks):
                task_time = task["time"]
                task_name = task["task"]
                recurring = task.get("recurring", "None")
                last_date_str = task.get("last_triggered_date")
                last_date = None

                if last_date_str:
                    try:
                        last_date = datetime.datetime.strptime(last_date_str, "%Y-%m-%d").date()
                    except Exception:
                        last_date = None

                remind = False

                if task_time == now_time:
                    if recurring == "None":
                        if last_date != today_date:
                            remind = True
                    elif recurring == "Daily":
                        if last_date != today_date:
                            remind = True
                    elif recurring == "Weekly":
                        weekday = task.get("weekday")
                        if weekday is None:
                            weekday = today_date.weekday()
                            task["weekday"] = weekday
                        if today_date.weekday() == weekday and last_date != today_date:
                            remind = True
                    elif recurring == "Monthly":
                        day = task.get("day")
                        if day is None:
                            day = today_date.day
                            task["day"] = day
                        if today_date.day == day and last_date != today_date:
                            remind = True

                if remind:
                    task["last_triggered_date"] = today_date.strftime("%Y-%m-%d")
                    self.root.after(0, self.show_popup, task_name)
                    self.play_sound()

            self.save_current_note()
            time.sleep(55)

    def show_popup(self, message):
        messagebox.showinfo("Reminder", f"Reminder: {message}")

    def play_sound(self):
        try:
            pygame.mixer.init()
            pygame.mixer.music.load(DEFAULT_SOUND)
            pygame.mixer.music.play()
        except Exception as e:
            print("Error playing sound:", e)

    def save_current_note(self):
        try:
            filename = f"{self.note_name}.json"
            with open(filename, "w") as f:
                json.dump(self.tasks, f)
        except Exception as e:
            print("Error saving note:", e)


def main():
    theme = "superhero"
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                theme = data.get("theme", theme)
        except Exception:
            pass

    style = tb.Style(theme=theme)
    root = style.master

    app = ReminderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
