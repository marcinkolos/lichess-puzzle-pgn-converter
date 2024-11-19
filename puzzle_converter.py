import chess
import chess.pgn
import zstandard as zstd
import pandas as pd
import os
from tkinter import *
from tkinter import messagebox, filedialog, ttk
import threading
import time

csv = None
theme_set = None
theme_dictionary = {}
progress = 0

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
    global theme_set, theme_dictionary
    theme_dictionary.clear()
    theme_set = sorted(set(word for themes in df['Themes'] for word in themes.split()))
    for theme in theme_set:
        theme_dictionary.update({theme: theme})
    return theme_dictionary

def count_theme_occurrences(df):
    global theme_set, theme_dictionary, progress
    progress = 0
    theme_dictionary.clear()
    theme_counts = df['Themes'].str.split().explode().value_counts()
    for i, theme in enumerate(theme_set):
        theme_dictionary[f'{theme} ({theme_counts.get(theme, 0):,})'] = theme
        progress = int((i + 1) / len(theme_set) * 100)
    return theme_dictionary

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
    global theme_dictionary, progress
    filtered = filter_by_theme(df, theme_dictionary[theme])
    for i in range(how_many):
        save_to_pgn_file(paginate(filtered, page + i, page_size), f'{file_path}_part{(i + 1)}.pgn')
        progress = int((i/how_many) * 100)

def draw_GUI():
    global stop_thread
    stop_thread = False

    root = Tk()
    root.title('Chess Puzzles')
    root.geometry('520x360')
    mainframe = ttk.Frame(root, padding='3 3 12 12')
    mainframe.grid(column=0, row=0, sticky=(N, W, E, S))
    mainframe.columnconfigure(0, weight=1)
    mainframe.rowconfigure(0, weight=1)

    ttk.Label(mainframe, text='CSV file path').grid(column=2, row=1, sticky=(W, E))
    
    input_path = StringVar()
    input_path_entry = ttk.Entry(mainframe, width=70, textvariable=input_path)
    input_path_entry.grid(column=2, row=2, sticky=(W, E))

    def handle_openfiledialog(*args):
        input_path.set(filedialog.askopenfilename(
            title='Select a CSV file', 
            filetypes=(('Zstandard CSV files', '*.csv.zst'), ('All files', '*.*'))    
        ))

    ttk.Button(mainframe, text='Browse...', command=handle_openfiledialog).grid(column=3, row=2, sticky=W)

    def handle_opencsv(*args):
        start = time.time()
        def task():
            try:
                global csv, progress
                file_path = input_path.get()
                if not os.path.exists(file_path) or not os.path.isfile(file_path):
                    messagebox.showerror('Error', 'File not found')
                    return

                chunk_size = 100000  # Adjust the chunk size as needed
                total_size = os.path.getsize(file_path)
                bytes_read = 0
                chunks = []

                dctx = zstd.ZstdDecompressor()
                with open(file_path, 'rb') as f:
                    with dctx.stream_reader(f) as reader:
                        df_iter = pd.read_csv(reader, usecols=['PuzzleId', 'FEN', 'Moves', 'Themes'], chunksize=chunk_size)
                        for chunk in df_iter:
                            bytes_read = f.tell()
                            chunks.append(chunk)
                            progress = int((bytes_read/total_size) * 100)

                csv = pd.concat(chunks, ignore_index=True)
                themes = read_themes(csv)
                button_countthemes.config(state='enabled')
                dropdown['values'] = list(themes.keys())  # Set the options
                selected_theme.set(list(themes.keys())[0])
                button_savepgn.config(state='enabled')
                messagebox.showinfo('CSV loaded', 'CSV loaded successfully')
            except UnicodeDecodeError as e:
                messagebox.showerror('Error', f'Unicode decode error: {e}')
            except ValueError as e:
                messagebox.showerror('Error', f'Value error: {e}')
            except Exception as e:
                messagebox.showerror('Error', f'An unexpected error occurred: {e}')
            finally:
                progress = 100
                print(f'Time elapsed: {time.time() - start} seconds')

        threading.Thread(target=task).start()

    ttk.Button(mainframe, text='Open CSV', command=handle_opencsv).grid(column=2, row=4, sticky=W)

    def handle_countthemes(*args):
        def task():
            start = time.time()
            global progress
            try:
                theme_occurrences = count_theme_occurrences(csv)
                dropdown['values'] = list(theme_occurrences.keys())  # Set the options
                selected_theme.set(list(theme_occurrences.keys())[0])
            except ValueError as e:
                print(e)
            finally:
                progress = 100
                print(f'Time elapsed: {time.time() - start} seconds')

        threading.Thread(target=task).start()

    button_countthemes = ttk.Button(
        mainframe, text='Count themes', 
        command=handle_countthemes,
        state='disabled'
    )
    button_countthemes.grid(column=2, row=5, sticky=W)

    ttk.Label(mainframe, text='Select theme').grid(column=2, row=6, sticky=(W, E))
    # Create a dropdown (Combobox)
    selected_theme = StringVar()
    dropdown = ttk.Combobox(
        mainframe, 
        textvariable=selected_theme,
        state='readonly'
    )
    dropdown.grid(column=2, row=7, sticky=(W, E))

    def validate_positive_number(new_value):
        '''Allow only numeric input.'''
        if new_value == '' or (new_value.isdigit() and int(new_value) > 0):
            return True
        return False

    # Validate that only numbers can be entered
    validate_cmd = root.register(validate_positive_number)

    ttk.Label(mainframe, text='How many positions in file').grid(column=2, row=8, sticky=(W, E))
    input_positions = IntVar(value=1)
    input_positions_entry = ttk.Entry(
        mainframe, 
        textvariable=input_positions,
        validate='key',  # Validate on key press
        validatecommand=(validate_cmd, '%P'),  # Pass the new value
    )
    input_positions_entry.grid(column=2, row=9, sticky=(W, E))

    ttk.Label(mainframe, text='Starting page').grid(column=2, row=10, sticky=(W, E))
    input_startpage = IntVar(value=1)
    input_startpage_entry = ttk.Entry(
        mainframe,
        textvariable=input_startpage,
        validate='key',  # Validate on key press
        validatecommand=(validate_cmd, '%P'),  # Pass the new value
    )
    input_startpage_entry.grid(column=2, row=11, sticky=(W, E))

    ttk.Label(mainframe, text='How many files to generate').grid(column=2, row=12, sticky=(W, E))
    input_filescount = IntVar(value=1)
    input_filescount_entry = ttk.Entry(
        mainframe, 
        textvariable=input_filescount,
        validate='key',  # Validate on key press
        validatecommand=(validate_cmd, '%P'),  # Pass the new value
    )
    input_filescount_entry.grid(column=2, row=13, sticky=(W, E))

    ttk.Label(mainframe, text='File name template').grid(column=2, row=14, sticky=(W, E))
    input_filesname = StringVar()
    input_filesname_entry = ttk.Entry(
        mainframe, 
        textvariable=input_filesname, 
    )
    input_filesname_entry.grid(column=2, row=15, sticky=(W, E))

    def handle_savefiledialog(*args):
        input_filesname.set(filedialog.asksaveasfilename(
            title='Select a PGN file name', 
            filetypes=(('PGN files', '*.pgn'), ('All files', '*.*'))    
    ))

    ttk.Button(
        mainframe, 
        text='Browse...', 
        command=handle_savefiledialog,
    ).grid(column=3, row=15, sticky=W)

    def handle_savepgn(*args):
        def task():
            start = time.time()
            global progress
            try:
                global csv
                if input_filesname.get() == '': 
                    messagebox.showerror('Error', 'File name template is empty')
                    return
                paginate_multiple(csv, selected_theme.get(), input_startpage.get() - 1, 
                                input_positions.get(), input_filescount.get(), input_filesname.get())
                messagebox.showinfo('PGN saved', 'PGN saved successfully')
            except ValueError:
                pass
            finally:
                progress = 100
                print(f'Time elapsed: {time.time() - start} seconds')

        threading.Thread(target=task).start()

    button_savepgn = ttk.Button(
        mainframe, 
        text='Save PGN', 
        command=handle_savepgn,
        state='disabled'
    )
    button_savepgn.grid(column=2, row=16, sticky=W)

    global progress_var, progress_bar
    progress_var = IntVar()
    progress_bar = ttk.Progressbar(mainframe, orient=HORIZONTAL, length=300, mode='determinate', variable=progress_var)
    progress_bar.grid(column=2, row=17, pady=10)

    value_label = ttk.Label(mainframe, text=str(progress_var.get()) + '%')
    value_label.grid(column=3, row=17)

    def on_close():
        '''Handle application close.'''
        global stop_thread
        stop_thread = True  # Signal the thread to stop
        root.destroy()      # Close the Tkinter window

    root.protocol('WM_DELETE_WINDOW', on_close)

    def update_progress_bar(progress_var):
        '''Update progress bar periodically.'''
        while not stop_thread:
            progress_var.set(progress)
            value_label['text'] = str(progress_var.get()) + '%'
            time.sleep(0.5)  # Update every second

    threading.Thread(target=update_progress_bar, args=(progress_var,), daemon=True).start()

    root.mainloop()


def main():
    draw_GUI()

if __name__ == '__main__':
    main()