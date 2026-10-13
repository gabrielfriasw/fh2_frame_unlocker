"""Start the original Azimuth interface with additional FPS choices."""
import argparse, os, sys, uuid
from pathlib import Path
import engine
APP_DATA=Path(os.environ.get("LOCALAPPDATA",str(Path.home())))/"FH2FPSUnlocker"
PREFERENCES=APP_DATA/"direct-settings.json"

def default_workspace():
    try:return Path(engine.load_json(PREFERENCES)["workspace"])
    except (OSError,ValueError,KeyError):return APP_DATA/"profile"

def setup_dialog():
    import tkinter as tk
    from tkinter import filedialog,messagebox
    root=tk.Tk();root.withdraw()
    try:
        exe=filedialog.askopenfilename(title="Select azimuth.exe",filetypes=[("Azimuth","azimuth.exe")])
        if not exe:return None
        game=engine.detect_game(Path(exe).parent)
        if not game:game=filedialog.askdirectory(title="Select FH2 folder containing Mount")
        if not game:return None
        workspace=APP_DATA/"profiles"/uuid.uuid4().hex
        engine.prepare(exe,game,workspace)
        engine.write_json(PREFERENCES,{"workspace":str(workspace.resolve())})
        messagebox.showinfo("Ready","The original Azimuth interface will open. Use its Frame rate row to select FPS.\n\nAbove 60 FPS the mod enforces real-time pacing. Higher limits are experimental; 180 previously crashed.\n\nClose the game to remove all memory patches.")
        return workspace
    finally:root.destroy()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--setup",action="store_true",help="Select the existing Azimuth installation")
    parser.add_argument("--workspace",type=Path,help="Settings and backup directory")
    parser.add_argument("--prepare",action="store_true",help="Prepare from --azimuth and --game-folder without launching")
    parser.add_argument("--azimuth",type=Path)
    parser.add_argument("--game-folder",type=Path)
    parser.add_argument("--verify",action="store_true",help="Verify profile without launching")
    parser.add_argument("--compatibility-report",action="store_true",help="Report Extra Options installation and startup log evidence without launching")
    parser.add_argument("--self-test",action="store_true",help="Check bundled GUI and patch modules without starting Azimuth")
    args=parser.parse_args();workspace=args.workspace or default_workspace()
    if args.self_test:
        import tkinter as tk
        import native_patches, parser_patches
        root=tk.Tk();root.withdraw();root.update_idletasks();root.destroy()
        native_patches.build_native_ui(0x140000000,0x200000000)
        parser_patches.parser_code(0x140000000)
        parser_patches.pacing_parser_code(0x140000000)
        parser_patches.dynamic_pacing()
        return
    if args.compatibility_report:
        import extra_options
        report=engine.compatibility_report(workspace)
        path=workspace/"compatibility-report.json"
        engine.write_json(path,report)
        summary=extra_options.report_summary(report)+"\n\nReport: "+str(path)
        if getattr(sys,"frozen",False):
            import tkinter as tk
            from tkinter import messagebox
            root=tk.Tk();root.withdraw();messagebox.showinfo("Extra Options compatibility",summary);root.destroy()
        else:print(summary)
        return
    if args.prepare:
        engine.require(args.azimuth and args.game_folder and args.workspace,"--prepare requires --azimuth, --game-folder and --workspace")
        engine.prepare(args.azimuth,args.game_folder,workspace)
        print("Prepared:",workspace);return
    if args.verify:
        engine.validate_profile(workspace);print("Verified:",workspace);return
    if args.setup or not (workspace/"profile.json").is_file():
        workspace=setup_dialog()
        if workspace is None:return
    engine.launch(workspace)

if __name__=="__main__":
    try:main()
    except Exception as exc:
        if getattr(sys,"frozen",False):
            import tkinter as tk
            from tkinter import messagebox
            root=tk.Tk();root.withdraw();messagebox.showerror("FH2 FPS Unlocker",str(exc));root.destroy()
        else:print(f"Stopped: {exc}",file=sys.stderr)
        sys.exit(1)
