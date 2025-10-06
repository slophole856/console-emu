import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import os
import getpass
import platform
import sys
import argparse
from pathlib import Path
import argparse
from pathlib import Path
import json
import base64

class VFSNode:
    def __init__(self, name):
        self.name = name

    def is_dir(self):
        return False

    def is_file(self):
        return False

class VFSFile(VFSNode):
    def __init__(self, name, content_bytes, encoding="raw"):
        super().__init__(name)
        self.content = content_bytes
        self.encoding = encoding      # utf-8, raw

    def is_file(self):
        return True

    def read_text(self, errors="replace"):
        if self.encoding == "utf-8":
            return self.content.decode("utf-8", errors=errors)
        else:
            return None

    def read_hex(self):
        return self.content.hex()

class VFSDir(VFSNode):
    def __init__(self, name):
        super().__init__(name)
        self.children = {}

    def is_dir(self):
        return True

    def add_child(self, node):
        self.children[node.name] = node

    def get_child(self, name):
        return self.children.get(name)

    def list_names(self):
        return sorted(self.children.keys())
        
def load_vfs_from_json(path: Path):
    def build_node(obj):
        t = obj.get("type")
        name = obj.get("name", "")
        if t == "dir":
            d = VFSDir(name)
            for child in obj.get("children", []):
                node = build_node(child)
                d.add_child(node)
            return d
        elif t == "file":
            enc = obj.get("encoding", "utf-8")
            raw = obj.get("content", "")
            if enc == "base64":
                try:
                    b = base64.b64decode(raw)
                except Exception:
                    b = b""
            elif enc == "utf-8":
                b = raw.encode("utf-8")
            else:
                b = raw.encode("utf-8")
            return VFSFile(name, b, encoding=enc if enc == "utf-8" else "raw")
        else:
            raise ValueError("Unknown node type: " + str(t))

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    root = build_node(data)
    if not root.is_dir():
        raise ValueError("Top-level VFS node must be a dir. Why you have no root folder")
    return root

def resolve_path(root: VFSDir, cwd_parts, path_str):
    if path_str == "":
        return root, []
    parts = [p for p in path_str.split("/") if p != ""]
    if path_str.startswith("/"):
        cur = root
        cur_parts = []
    else:
        cur = get_node_by_parts(root, cwd_parts)
        cur_parts = list(cwd_parts)
    for p in parts:
        if p == ".":
            continue
        if p == "..":
            if cur_parts:
                cur_parts.pop()
                cur = get_node_by_parts(root, cur_parts)
            else:
                cur = root
                cur_parts = []
            continue
        if not cur or not cur.is_dir():
            return None, None
        nxt = cur.get_child(p)
        if nxt is None:
            return None, None
        cur = nxt
        cur_parts.append(p)
    return cur, cur_parts

def get_node_by_parts(root, parts):
    cur = root
    for p in parts:
        if not isinstance(cur, VFSDir):
            return None
        cur = cur.get_child(p)
        if cur is None:
            return None
    return cur

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