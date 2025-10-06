import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import os
import getpass
import platform
import sys

class ShellEmu:
    def __init__(self):
        self.root = tk.Tk()
        
        try:
            self.user = os.getlogin()
        except Exception:
            self.user = getpass.getuser() or "unknown"
        self.host = platform.node() or "localhost"

        self.root.title("Emulator " + "[" + self.user + "@" + self.host + "]")
        self.root.geometry("640x480")

        self.history = ScrolledText(self.root, width=10, state='disabled', font=("Courier New", 10))
        self.history.pack(fill=tk.BOTH, side=tk.TOP, expand=True)

        self.input_field = tk.Entry(self.root, font=("Courier New", 10))
        self.input_field.pack(fill=tk.BOTH, side=tk.BOTTOM, expand=True)

        self.input_field.bind("<Return>", self.execute_command)
        self.input_field.focus()

        self.root.mainloop()
        
    def start_script(self):
        p = Path(self.start_path)
        if p.exists() and p.is_file():
            with open(self.start_path) as file:
                for line in file:
                    if not self.execute_command_bad(line):
                        break
        else:
            print("Specified start script " + self.start_path + " doesn't exist.")

    def execute_command(self, event):
        full = self.input_field.get()
        
        tokens = full.split()
        
        if (len(tokens) == 0):
            return
            
        self.output("> " + full)
        
        command = tokens[0]
        args = tokens[1:]
        
        if command == "exit":
            self.cm_exit()
        elif command == "ls" or command == "dir":
            self.output(command + "".join(args))
        elif command == "cd":
            self.output(command + "".join(args))
        
        self.input_field.delete(0, tk.END)
        
        self.history.yview(tk.END)
        #self.history.update()
        
    def output(self, text):
        self.history.config(state="normal")
        self.history.insert(tk.INSERT, text + '\n')
        self.history.config(state="disabled")
        
    def cm_exit(self):
        self.root.destroy()
        #exit(0)
        
def main():
    emu = ShellEmu()
    
if __name__ == "__main__":
    main()