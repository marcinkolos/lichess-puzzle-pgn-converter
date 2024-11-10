import chess
import chess.pgn
import pandas as pd
from tkinter import *
from tkinter import messagebox
from tkinter import filedialog
from tkinter import ttk

csv = None

def position_to_pgn(fen, moves_string, event):
    game = chess.pgn.Game()
    game.headers['Event'] = event
    game.setup(fen)
    moves = moves_string.split()
    node = game.add_main_variation(chess.Move.from_uci(moves[0]))
    for move in moves[1:]:
        node = node.add_main_variation(chess.Move.from_uci(move))
    return game

def read_csv(file_path):
    df = pd.read_csv(file_path, usecols=['PuzzleId', 'FEN', 'Moves', 'Themes'])
    return df

def read_themes(df):
    themes_set = set(word for themes in df['Themes'] for word in themes.split())
    return list(themes_set)

def filter_by_theme(df, theme):
    return df[df['Themes'].str.contains(theme)]

def paginate(df, page, page_size): # page is 0-indexed
    return df.iloc[page * page_size: (page + 1) * page_size]

def save_to_pgn_file(df, file_path):
    with open(file_path, 'w') as f:
        for i in range(len(df)):
            game = position_to_pgn(df.iloc[i]['FEN'], df.iloc[i]['Moves'], df.iloc[i]['PuzzleId'])
            f.write(str(game) + '\n\n')

def paginate_multiple(df, theme, page, page_size, how_many, file_path):
    for i in range(how_many):
        save_to_pgn_file(paginate(filter_by_theme(df, theme), page + i, page_size), f'{file_path}_part{(i + 1)}.pgn')

def draw_GUI():
    root = Tk()
    root.title('Chess Puzzles')
    root.geometry('520x360')
    mainframe = ttk.Frame(root, padding="3 3 12 12")
    mainframe.grid(column=0, row=0, sticky=(N, W, E, S))
    mainframe.columnconfigure(0, weight=1)
    mainframe.rowconfigure(0, weight=1)

    ttk.Label(mainframe, text="CSV file path").grid(column=2, row=1, sticky=(W, E))
    
    input_path = StringVar()
    input_path_entry = ttk.Entry(mainframe, width=70, textvariable=input_path)
    input_path_entry.grid(column=2, row=2, sticky=(W, E))

    def handle_openfiledialog(*args):
        input_path.set(filedialog.askopenfilename(
            title="Select a CSV file", 
            filetypes=(("Zstandard CSV files", "*.csv.zst"), ("All files", "*.*"))    
        ))

    ttk.Button(mainframe, text="Browse...", command=handle_openfiledialog).grid(column=3, row=2, sticky=W)

    def handle_opencsv(*args):
        try:
            global csv
            csv = read_csv(input_path.get())
            themes = read_themes(csv)
            dropdown['values'] = themes  # Set the options
            messagebox.showinfo("CSV loaded", "CSV loaded successfully")
        except ValueError:
            pass

    ttk.Button(mainframe, text="Open CSV", command=handle_opencsv).grid(column=2, row=4, sticky=W)

    ttk.Label(mainframe, text="Select theme").grid(column=2, row=5, sticky=(W, E))
    # Create a dropdown (Combobox)
    selected_theme = StringVar()
    dropdown = ttk.Combobox(mainframe, textvariable=selected_theme)
    dropdown.grid(column=2, row=6, sticky=(W, E))

    def handle_savepgn(*args):
        try:
            global csv
            paginate_multiple(csv, selected_theme.get(), input_startpage.get() + 1, input_positions.get(), input_filescount.get(), input_filesname.get())
            messagebox.showinfo("PGN saved", "PGN saved successfully")
        except ValueError:
            pass

    ttk.Label(mainframe, text="How many positions in file").grid(column=2, row=7, sticky=(W, E))
    input_positions = IntVar()
    input_positions_entry = ttk.Entry(mainframe, textvariable=input_positions)
    input_positions_entry.grid(column=2, row=8, sticky=(W, E))

    ttk.Label(mainframe, text="Starting page").grid(column=2, row=9, sticky=(W, E))
    input_startpage = IntVar()
    input_startpage_entry = ttk.Entry(mainframe, textvariable=input_startpage)
    input_startpage_entry.grid(column=2, row=10, sticky=(W, E))

    ttk.Label(mainframe, text="How many files to generate").grid(column=2, row=11, sticky=(W, E))
    input_filescount = IntVar()
    input_filescount_entry = ttk.Entry(mainframe, textvariable=input_filescount)
    input_filescount_entry.grid(column=2, row=12, sticky=(W, E))

    ttk.Label(mainframe, text="File name template").grid(column=2, row=13, sticky=(W, E))
    input_filesname = StringVar()
    input_filesname_entry = ttk.Entry(mainframe, textvariable=input_filesname)
    input_filesname_entry.grid(column=2, row=14, sticky=(W, E))

    def handle_savefiledialog(*args):
        input_filesname.set(filedialog.asksaveasfilename(
            title="Select a PGN file name", 
            filetypes=(("PGN files", "*.pgn"), ("All files", "*.*"))    
    ))

    ttk.Button(mainframe, text="Browse...", command=handle_savefiledialog).grid(column=3, row=14, sticky=W)

    ttk.Button(mainframe, text="Save PGN", command=handle_savepgn).grid(column=2, row=16, sticky=W)

    root.mainloop()


def main():
    draw_GUI()

if __name__ == '__main__':
    main()