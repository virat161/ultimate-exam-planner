import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import json, os, webbrowser, time
from pathlib import Path

DATA_FILE = Path.home() / "exam_planner_data.json"


# ========== DATA ==========
def load():
    if not DATA_FILE.exists():
        return {}
    try:
        return json.load(open(DATA_FILE, "r"))
    except:
        return {}


def save(data):
    json.dump(data, open(DATA_FILE, "w"), indent=4)


def ensure_structure(exam, sub):
    data = load()
    if exam not in data:
        data[exam] = {}
    if sub not in data[exam] or not isinstance(data[exam][sub], dict):
        data[exam][sub] = {
            "topics": [],
            "resources": [],
            "notes": ""
        }
    save(data)


def open_item(path):
    try:
        os.startfile(path)
    except:
        webbrowser.open(path)


frames = {}
selected_exam = None
active_subject = None


def show(name):
    for f in frames.values():
        f.pack_forget()
    frames[name].pack(fill=BOTH, expand=True)


# ========== EXAM SCREEN ==========
def exam_screen(root):
    f = ttk.Frame(root, padding=10)

    entry = ttk.Entry(f)
    entry.pack(fill=X, pady=5)

    lst = tk.Listbox(f, height=10)
    lst.pack(fill=BOTH, expand=True)

    def refresh():
        lst.delete(0, tk.END)
        for e in load().keys():
            lst.insert(tk.END, e)

    def add():
        n = entry.get().strip()
        if not n:
            return
        data = load()
        if n not in data:
            data[n] = {}
            save(data)
        entry.delete(0, tk.END)
        refresh()

    def open_exam():
        if not lst.curselection():
            return
        selected_exam.set(lst.get(lst.curselection()[0]))
        active_subject.set("")
        frames["planner"].refresh()
        show("planner")

    ttk.Button(f, text="Add Exam", bootstyle="success", command=add).pack(pady=4)
    ttk.Button(f, text="Open", bootstyle="info", command=open_exam).pack()

    refresh()
    return f


# ========== PLANNER SCREEN ==========
def planner_screen(root):
    f = ttk.Frame(root, padding=10)

    title = ttk.Label(f, text="", font="-size 14 -weight bold")
    title.pack(anchor=W)

    ttk.Button(f, text="< Back", bootstyle="secondary",
               command=lambda: show("exams")).pack(anchor=E)

    body = ttk.Frame(f)
    body.pack(fill=BOTH, expand=True)

    # -------- LEFT PANEL (SUBJECTS) --------
    left = ttk.Frame(body)
    left.pack(side=LEFT, fill=Y)

    sub_entry = ttk.Entry(left)
    sub_entry.pack(fill=X, pady=3)

    sub_list = tk.Listbox(left, height=14)
    sub_list.pack(fill=Y, expand=True)

    def load_subjects():
        sub_list.delete(0, tk.END)
        for s in load().get(selected_exam.get(), {}):
            sub_list.insert(tk.END, s)

    def add_subject():
        exam = selected_exam.get()
        name = sub_entry.get().strip()
        if not name:
            return
        ensure_structure(exam, name)
        sub_entry.delete(0, tk.END)
        load_subjects()

    def delete_subject():
        if not sub_list.curselection():
            return
        exam = selected_exam.get()
        sub = sub_list.get(sub_list.curselection()[0])

        data = load()
        del data[exam][sub]
        save(data)
        load_subjects()

    ttk.Button(left, text="Add Subject", bootstyle="success", command=add_subject).pack(fill=X, pady=3)
    ttk.Button(left, text="Delete Subject", bootstyle="danger", command=delete_subject).pack(fill=X)

    # -------- RIGHT PANEL --------
    right = ttk.Frame(body)
    right.pack(side=RIGHT, fill=BOTH, expand=True)

    tabs = ttk.Notebook(right)
    t_tab = ttk.Frame(tabs)
    n_tab = ttk.Frame(tabs)
    r_tab = ttk.Frame(tabs)
    tabs.add(t_tab, text="Topics")
    tabs.add(n_tab, text="Notes")
    tabs.add(r_tab, text="Resources / Pomodoro")
    tabs.pack(fill=BOTH, expand=True)

    # ========== TOPICS TAB ==========
    t_entry = ttk.Entry(t_tab)
    t_entry.pack(fill=X, pady=3)

    topic_list = tk.Listbox(t_tab)
    topic_list.pack(fill=BOTH, expand=True)

    progress_var = tk.IntVar()
    progress_label = ttk.Label(t_tab, text="0%")
    progress_label.pack()

    def load_topics():
        topic_list.delete(0, tk.END)
        if not active_subject.get(): return

        exam = selected_exam.get()
        sub = active_subject.get()
        ensure_structure(exam, sub)

        data = load()
        topics = data[exam][sub]["topics"]

        # ---- backward compatibility repair ----
        fixed = []
        for t in topics:
            if isinstance(t, dict):
                nm = t.get("topic") or t.get("name") or "Untitled"
                st = t.get("status") or "Not Started"
            else:
                nm, st = str(t), "Not Started"
            fixed.append({"topic": nm, "status": st})
        data[exam][sub]["topics"] = fixed
        save(data)
        topics = fixed
        # --------------------------------------

        total = len(topics)
        done = sum(1 for t in topics if t["status"] == "Completed")
        pct = int(done / total * 100) if total else 0

        progress_var.set(pct)
        progress_label.config(text=f"{done}/{total} • {pct}% Complete")

        icon_map = {
            "Not Started": "🔴",
            "In Progress": "🟡",
            "Completed": "🟢"
        }

        for t in topics:
            topic_list.insert(tk.END, f"{icon_map.get(t['status'],'🔴')} {t['topic']} [{t['status']}]")

    def add_topic():
        if not active_subject.get(): return
        exam = selected_exam.get()
        sub = active_subject.get()
        ensure_structure(exam, sub)

        name = t_entry.get().strip()
        if not name: return

        data = load()
        data[exam][sub]["topics"].append({"topic": name, "status": "Not Started"})
        save(data)

        t_entry.delete(0, tk.END)
        load_topics()

    def change_status(e=None):
        if not topic_list.curselection(): return
        i = topic_list.curselection()[0]

        exam = selected_exam.get()
        sub = active_subject.get()
        data = load()

        seq = ["Not Started", "In Progress", "Completed"]

        cur = data[exam][sub]["topics"][i]["status"]
        data[exam][sub]["topics"][i]["status"] = seq[(seq.index(cur)+1)%3]

        save(data)
        load_topics()

    def delete_topic():
        if not topic_list.curselection():
            return

        i = topic_list.curselection()[0]
        exam = selected_exam.get()
        sub = active_subject.get()

        data = load()
        del data[exam][sub]["topics"][i]
        save(data)

        load_topics()

    topic_list.bind("<Double-Button-1>", change_status)

    btn_bar = ttk.Frame(t_tab)
    btn_bar.pack(pady=3)

    ttk.Button(btn_bar, text="Add Topic", bootstyle="success", command=add_topic).pack(side=LEFT, padx=3)
    ttk.Button(btn_bar, text="Delete Topic", bootstyle="danger", command=delete_topic).pack(side=LEFT, padx=3)

    # ========== NOTES TAB ==========
    notes = tk.Text(n_tab, wrap="word")
    notes.pack(fill=BOTH, expand=True)

    def load_notes():
        notes.delete("1.0", tk.END)
        if not active_subject.get(): return
        exam = selected_exam.get()
        sub = active_subject.get()
        ensure_structure(exam, sub)
        notes.insert(tk.END, load()[exam][sub]["notes"])

    def save_notes():
        exam = selected_exam.get()
        sub = active_subject.get()
        data = load()
        ensure_structure(exam, sub)
        data[exam][sub]["notes"] = notes.get("1.0", tk.END).strip()
        save(data)
        messagebox.showinfo("Saved", "Notes saved")

    ttk.Button(n_tab, text="Save Notes", bootstyle="success", command=save_notes).pack(pady=5)

    # ========== RESOURCES TAB ==========
    res_title = ttk.Entry(r_tab)
    res_title.insert(0, "Resource")
    res_title.pack(fill=X, pady=2)

    res_link = ttk.Entry(r_tab)
    res_link.pack(fill=X, pady=2)

    def browse():
        p = filedialog.askopenfilename()
        if p:
            res_link.delete(0, tk.END)
            res_link.insert(0, p)

    ttk.Button(r_tab, text="Browse", command=browse).pack(pady=2)

    res_list = tk.Listbox(r_tab)
    res_list.pack(fill=BOTH, expand=True)

    def load_resources():
        res_list.delete(0, tk.END)
        if not active_subject.get(): return
        exam = selected_exam.get()
        sub = active_subject.get()
        ensure_structure(exam, sub)
        for r in load()[exam][sub]["resources"]:
            res_list.insert(tk.END, r["title"])

    def add_res():
        if not active_subject.get(): return
        exam = selected_exam.get()
        sub = active_subject.get()
        ensure_structure(exam, sub)

        data = load()
        data[exam][sub]["resources"].append({
            "title": res_title.get().strip() or "Resource",
            "link": res_link.get().strip()
        })
        save(data)
        load_resources()
        res_link.delete(0, tk.END)

    def delete_res():
        if not res_list.curselection(): return
        i = res_list.curselection()[0]
        exam = selected_exam.get()
        sub = active_subject.get()

        data = load()
        del data[exam][sub]["resources"][i]
        save(data)
        load_resources()

    def open_res(e=None):
        i = res_list.curselection()[0]
        exam = selected_exam.get()
        sub = active_subject.get()
        link = load()[exam][sub]["resources"][i]["link"]
        open_item(link)

    res_list.bind("<Double-Button-1>", open_res)

    rb = ttk.Frame(r_tab)
    rb.pack(pady=3)

    ttk.Button(rb, text="Add Resource", bootstyle="info", command=add_res).pack(side=LEFT, padx=3)
    ttk.Button(rb, text="Delete Resource", bootstyle="danger", command=delete_res).pack(side=LEFT, padx=3)

    # ===== Pomodoro =====
    timer_lbl = ttk.Label(r_tab, text="00:00", font="-size 16 -weight bold")
    timer_lbl.pack(pady=5)

    running = {"on": False}

    def start_timer(mins):
        running["on"] = True
        secs = mins * 60
        while secs >= 0 and running["on"]:
            m, s = secs // 60, secs % 60
            timer_lbl.config(text=f"{m:02}:{s:02}")
            timer_lbl.update()
            time.sleep(1)
            secs -= 1

    def stop_timer():
        running["on"] = False
        timer_lbl.config(text="00:00")

    tb = ttk.Frame(r_tab)
    tb.pack(pady=3)

    ttk.Button(tb, text="25m", command=lambda: start_timer(25)).pack(side=LEFT, padx=2)
    ttk.Button(tb, text="5m", command=lambda: start_timer(5)).pack(side=LEFT, padx=2)
    ttk.Button(tb, text="Stop", bootstyle="danger", command=stop_timer).pack(side=LEFT, padx=2)

    # ===== SUBJECT SELECT =====
    def select_subject(e=None):
        if not sub_list.curselection(): return
        active_subject.set(sub_list.get(sub_list.curselection()[0]))
        load_topics()
        load_notes()
        load_resources()

    sub_list.bind("<<ListboxSelect>>", select_subject)

    def refresh():
        title.config(text=f"Planner — {selected_exam.get()}")
        load_subjects()
        topic_list.delete(0, tk.END)
        res_list.delete(0, tk.END)
        notes.delete("1.0", tk.END)

    f.refresh = refresh
    return f


# ========== RUN APP ==========
root = ttk.Window(themename="flatly")
root.title("Ultimate Exam Planner v1.0")
root.geometry("1100x700")

selected_exam = tk.StringVar(root)
active_subject = tk.StringVar(root)

frames["exams"] = exam_screen(root)
frames["planner"] = planner_screen(root)

show("exams")
root.mainloop()
