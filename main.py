import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import os
import getpass
import platform
import sys
import argparse
from pathlib import Path
import json
import base64
import datetime

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
        
        if self.vfs_path == "":
            print("No VFS specified. Using default.")
        
        if self.start_path == "":
            print("No start script specified.")
        else:
            self.start_script()

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
        elif command == "clear":
            self.cm_clear()
        elif command == "wc":
            self.cm_ws(args)
        elif command == "date":
            self.cm_date()
        elif command == "mv":
            self.cm_mv(args)
        elif command  == "echo":
            self.cm_echo(" ".join(args))
        elif command == "help":
            self.cm_help()
        elif command == "ls" or command == "dir":
            self.cm_ls(args)
        elif command == "cd":
            self.cm_cd(args)
        elif command == "pwd":
            self.cm_pwd()
        elif command == "cat":
            self.cm_cat(args)
        elif command == "info":
            self.cm_info(args)
        elif command == "tree":
            self.cm_tree(args)
        elif command == "tail":
            self.cm_tail(args)
        elif command == "conf-dump":
            self.cm_confdump()
        elif command == "mkdir":
            self.cm_mkdir(args)
        elif command == "rmdir":
            self.cm_rmdir(args)
        elif command == "chmod":
            self.cm_chmod(args)
        else:
            self.output("No such command: " + command)
        
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
        elif command == "clear":
            self.cm_clear()
        elif command == "wc":
            self.cm_ws(args)
        elif command == "date":
            self.cm_date()
        elif command == "mv":
            self.cm_mv(args)
        elif command  == "echo":
            self.cm_echo(" ".join(args))
        elif command == "help":
            self.cm_help()
        elif command == "ls" or command == "dir":
            self.cm_ls(args)
        elif command == "cd":
            self.cm_cd(args)
        elif command == "pwd":
            self.cm_pwd()
        elif command == "cat":
            self.cm_cat(args)
        elif command == "info":
            self.cm_info(args)
        elif command == "tree":
            self.cm_tree(args)
        elif command == "tail":
            self.cm_tail(args)
        elif command == "conf-dump":
            self.cm_confdump()
        elif command == "mkdir":
            self.cm_mkdir(args)
        elif command == "rmdir":
            self.cm_rmdir(args)
        elif command == "chmod":
            self.cm_chmod(args)
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
        
    def cm_clear(self):
        self.history.config(state="normal")
        self.history.delete(1.0, tk.END)
        self.history.config(state="disabled")
    
    def cm_ws(self, args):
        if not args:
            self.output("Usage: wc <file>")
            return

        target = args[0]
        node, _ = self._resolve_or_report(target)
        if node is None:
            return

        if node.is_dir():
            self.output("Error. wc: is a directory")
            return

        text = node.read_text()
        if text is None:
            size = len(node.content)
            self.output(f"{0:7} {0:7} {size:7} {target}")
            return

        lines = text.splitlines()
        words = text.split()
        bytes_count = len(node.content)

        self.output(f"{len(lines):7} {len(words):7} {bytes_count:7} {target}")
        
    def cm_date(self):
        now = datetime.datetime.now()
        self.output(now.strftime("%Y-%m-%d %H:%M:%S"))
        
    def cm_mv(self, args):
        if len(args) < 2:
            self.output("Usage: mv <source> <destination>")
            return

        src, dst = args[0], args[1]

        src_node, src_parts = self._resolve_or_report(src)
        if src_node is None:
            return

        if not src_parts:
            self.output("Error. mv: cannot move root directory")
            return

        src_parent = get_node_by_parts(self.vfs_root, src_parts[:-1])
        if not src_parent or not src_parent.is_dir():
            self.output("Error. mv: source parent not found")
            return

        dst_node, dst_parts = self._resolve_or_report(dst)
        if dst_node and dst_node.is_dir():
            new_name = src_parts[-1]
            dst_parent = dst_node
        else:
            if "/" in dst:
                parent_path, new_name = dst.rsplit("/", 1)
                dst_parent, _ = self._resolve_or_report(parent_path)
                if dst_parent is None or not dst_parent.is_dir():
                    self.output(f"Error. mv: destination parent '{parent_path}' not found")
                    return
            else:
                dst_parent = get_node_by_parts(self.vfs_root, self.cwd_parts)
                new_name = dst

        if dst_parent.get_child(new_name):
            self.output(f"Error. mv: target '{new_name}' already exists in destination")
            return

        del src_parent.children[src_parts[-1]]
        src_node.name = new_name
        dst_parent.add_child(src_node)

        self.output(f"Ok. moved '{src}' to '{dst}'")
        
    def cm_echo(self, text):
        self.output(text)
        
    def cm_help(self):
        self.output("no")
        
    def cm_ls(self, args):
        if not self.vfs_root:
            self.output("Error. No VFS loaded. Cannot list directories.")
            return
        
        target = args[0] if args else ""
        node, parts = self._resolve_or_report(target)
        if node is None:
            return
        if node.is_dir():
            for name in node.list_names():
                child = node.get_child(name)
                marker = "/" if child.is_dir() else ""
                self.output(name + marker)
        else:
            self.output(node.name)
        
    def cm_cd(self, args):
        if not self.vfs_root:
            self.output("Error. No VFS loaded. Cannot list directories.")
            return
                
        if not self.vfs_root:
            self.output("Error. No VFS loaded.")
            return
        target = args[0] if args else ""
        node, parts = resolve_path(self.vfs_root, self.cwd_parts, target) if target != "" else (self.vfs_root, [])
        if node is None or not node.is_dir():
            self.output("No such directory: " + (target or "/"))
            return
        self.cwd_parts = parts
        
    def cm_pwd(self):
        self.output("/" + "/".join(self.cwd_parts))

    def cm_cat(self, args):
        if not args:
            self.output("Usage: cat <file>")
            return
        target = args[0]
        node, parts = self._resolve_or_report(target)
        if node is None:
            return
        if node.is_dir():
            self.output("Error. cat: is a directory")
            return
        # attempt to show text if it's utf-8
        text = node.read_text()
        if text is not None:
            self.output(text)
        else:
            # show hexdump for binary
            self.output("[binary file] hex:")
            hexs = node.read_hex()
            # chunk hex for readability
            for i in range(0, len(hexs), 64):
                self.output(hexs[i:i+64])
        
    def cm_confdump(self):
        self.output(f"vfs_path={self.vfs_path}")
        self.output(f"start_path={self.start_path}")
        
    def cm_tree(self, args):
        if not self.vfs_root:
            self.output("Error. No VFS loaded.")
            return
        
        target = args[0] if args else ""
        node, _ = self._resolve_or_report(target)
        if node is None:
            return

        def walk(node, prefix=""):
            if node.is_dir():
                self.output(prefix + node.name + "/")
                children = node.list_names()
                for i, name in enumerate(children):
                    child = node.get_child(name)
                    last = i == len(children) - 1
                    walk(child, prefix + ("    " if last else "│   "))
            else:
                self.output(prefix + node.name)
        
        walk(node)
        
    def cm_tail(self, args):
        if not args:
            self.output("Usage: tail <file> [lines]")
            return
        
        target = args[0]
        lines_to_show = int(args[1]) if len(args) > 1 else 10
        
        node, _ = self._resolve_or_report(target)
        if node is None:
            return
        
        if node.is_dir():
            self.output("Error. tail: is a directory")
            return
        
        text = node.read_text()
        if text is None:
            self.output("Error. tail: binary file")
            return
        
        lines = text.splitlines()
        for line in lines[-lines_to_show:]:
            self.output(line)
            
    def cm_rmdir(self, args):
        if not args:
            self.output("Usage: rmdir <dir>")
            return

        target = args[0]
        node, parts = self._resolve_or_report(target)
        if node is None:
            return

        if not node.is_dir():
            self.output(f"Error. rmdir: {target} is not a directory")
            return

        if node.list_names():
            self.output(f"Error. rmdir: {target} is not empty")
            return

        if parts:
            parent = get_node_by_parts(self.vfs_root, parts[:-1])
            if parent and parent.is_dir():
                del parent.children[parts[-1]]
                self.output(f"Ok. removed {target}")
        else:
            self.output("Error. Cannot remove root directory")

    def cm_chmod(self, args):
        if len(args) < 2:
            self.output("Usage: chmod <mode> <file|dir>")
            return

        mode = args[0]
        target = args[1]
        node, _ = self._resolve_or_report(target)
        if node is None:
            return

        node.permissions = mode  # store in memory only
        self.output(f"Ok. {target} permissions set to {mode}")
       
    def cm_mkdir(self, args):
        if not args:
            self.output("Usage: mkdir <dir>")
            return

        target = args[0]
        if "/" in target:
            parent_path, new_dir_name = target.rsplit("/", 1)
        else:
            parent_path, new_dir_name = "", target

        parent_node, parent_parts = self._resolve_or_report(parent_path)
        if parent_node is None or not parent_node.is_dir():
            self.output(f"Error. mkdir: cannot create directory '{target}': parent does not exist")
            return

        if parent_node.get_child(new_dir_name):
            self.output(f"Error. mkdir: cannot create directory '{target}': already exists")
            return

        new_dir = VFSDir(new_dir_name)
        parent_node.add_child(new_dir)
        self.output(f"Ok. directory '{target}' created")
        
    def _resolve_or_report(self, target):
        if not self.vfs_root:
            self.output("Error. No VFS loaded.")
            return None, None
        if target == "":
            node = get_node_by_parts(self.vfs_root, self.cwd_parts)
            return node, list(self.cwd_parts)
        node, parts = resolve_path(self.vfs_root, self.cwd_parts, target)
        if node is None:
            self.output("No such file or directory: " + target)
            return None, None
        return node, parts
        
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vfs-path", help="VFS location on drive", required=False, default="")
    parser.add_argument("--start-path", help="Start script location on drive", required=False, default="")
    args = vars(parser.parse_args())
    
    emu = ShellEmu(args.get("vfs_path", ""), args.get("start_path", ""))
    
if __name__ == "__main__":
    main()