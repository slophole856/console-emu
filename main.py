import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import os
import getpass
import platform
import sys
import argparse
from pathlib import Path

class ShellEmu:
    def __init__(self, vfs_path, start_path):
        self.vfs_path = vfs_path
        self.start_path = start_path
        
        self.vfs_root = None
        if self.vfs_path:
            p = Path(self.vfs_path)
            if p.exists():
                try:
                    self.vfs_root = load_vfs_from_json(p)
                except Exception as e:
                    print(f"Failed to load VFS: {e}", file=sys.stderr)
                    self.vfs_root = None
            else:
                print("VFS file not found:", self.vfs_path)

        self.cwd_parts = []
        
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
        elif command == "help":
            self.cm_help()
        elif command == "ls" or command == "dir":
            self.output(command + "".join(args))
        elif command == "cd":
            self.output(command + "".join(args))
        elif command == "conf-dump":
            self.cm_confdump()
        else:
            self.output("No such command: " + command)
            return False
        
        self.input_field.delete(0, tk.END)
        
        self.history.yview(tk.END)
        #self.history.update()
        
    def execute_command_bad(self, full):      
            tokens = full.split()
            
            if (len(tokens) == 0):
                return True # not a fail so probably keep going it's fine
                
            self.output("> " + full)
            
            command = tokens[0]
            args = tokens[1:]
            
            if command == "exit":
                self.cm_exit()
            elif command == "help":
                self.cm_help()
            elif command == "ls" or command == "dir":
                self.output(command + "".join(args))
            elif command == "cd":
                self.output(command + "".join(args))
            elif command == "conf-dump":
                self.cm_confdump()
            else:
                self.output("No such command: " + command)
                return False
                
            self.history.yview(tk.END)
            return True
        
    def output(self, text):
        self.history.config(state="normal")
        self.history.insert(tk.INSERT, text + '\n')
        self.history.config(state="disabled")
        
    def cm_exit(self):
        self.root.destroy()
        #exit(0)
        
    def cm_confdump(self):
        self.output(f"vfs_path={self.vfs_path}")
        self.output(f"start_path={self.start_path}")
        
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vfs-path", help="VFS location on drive", required=False, default="")
    parser.add_argument("--start-path", help="Start script location on drive", required=False, default="")
    args = vars(parser.parse_args())
    
    emu = ShellEmu(args.get("vfs_path", ""), args.get("start_path", ""))
    
if __name__ == "__main__":
    main()