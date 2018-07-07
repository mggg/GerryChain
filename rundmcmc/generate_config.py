import pandas as pd
import geopandas as gp
import tkinter as tk
from tkinter import filedialog
import configparser

# GLOBAL WINDOW OPTIONS
col1 = "white"
col2 = "#B0E0E6"
windowSize = [750, 425]
offset = 0.01

# GLOBAL VARIABLES
config = configparser.ConfigParser()
# GRAPH SOURCE
gSource = ''
# GRAPH DATA
ID = ''
pop = ''
area = ''
cd = ''
# VOTE SOURCE
vSource = ''
vSourceID = ''
# VOTE DATA
vcols = []
# VALIDITY
vfuncs = []
# EVALUATION SCORES
efuncs = []
columns = []
columnNameChoices = {}
# EVALUATION_SCORES_DATA
evalScoreLogType = ""
vistype = ""
# MARKOV CHAIN
num_steps = ""
proposal = ""
accept = ""
cFileName = ''
validOptions = [
    "L1_reciprocal_polsby_popper",
    "within_percent_of_ideal_population",
    "fast_connected",
    "refuse_new_splits",
    "no_vanishing_districts"
]
evalOptions = [
    "efficiency_gap",
    "mean_median",
    "mean_thirdian",
    "L1_reciprocal_polsby_popper",
    "normalized_efficiency_gap",
    "polsby_popper_updater"
]
propOptions = [
    "propose_random_flip"
]
visOptions = {
        "write_hists": "histogram(plot)",
        "write_p_values": "p_value(report)",
        "write_flips": "each step(json)"
}


def callback():
    """
    Main function of the Process button to pull out the text entry fields.
    :return: Strings of all the column names specified.
    """
    global cFileName, config, gSource, vSource, gcsvvar, num_steps
    global proposal, vfuncs, efuncs, vchoices

    # GRAPH DATA
    config["GRAPH_SOURCE"] = {"gSource": gSource}
    config["GRAPH_DATA"] = {
            "ID": gid.get(),
            "pop": gpop.get(),
            "cd": gcd.get(),
            "area": garea.get()}

    # VOTE SOURCE
    if gcsvvar.get() == 1:
        config["VOTE_DATA_SOURCE"] = {"vSource": vSource, "vSourceID": vid.get()}
        vcols = vdata.get().split(',')
        config["VOTE_DATA"] = {"col" + str(x): vcols[x] for x in range(len(vcols))}
    # VALIDITY
    if len(vfuncs) > 0:
        config['VALIDITY'] = {"col" + str(i): vfuncs[i] for i in range(len(vfuncs))}

    # EVALUATION SCORES
    if len(efuncs) > 0:
        config['EVALUATION_SCORES'] = {"col" + str(i): efuncs[i] for i in range(len(efuncs))}
    config['EVALUATION_SCORES_LOG'] = {}

    # TODO: standardize scoring types and outputs
    for key, in visOptions.keys():
        if vchoices[key].get():
            config['EVALUATION_SCORES_LOG']['col' + key] = key
    config['SAVEFILENAME'] = {}
    config['SAVEFILENAME']['write_hists'] = box1.get()
    config['SAVEFILENAME']['write_flips'] = box2.get()
    config['SAVEFILENAME']['write_p_values'] = box3.get()

    # CHAIN CONFIG
    config['MARKOV_CHAIN'] = {}
    num_steps = numstepsdata.get()
    if num_steps is not None:
        config['MARKOV_CHAIN']['num_steps'] = num_steps

    proposal = propvar.get()
    if proposal is not None:
        config['MARKOV_CHAIN']['proposal'] = proposal

    # TODO: add acceptance functions
    if objectiveFunc.get() is not "Objective Function":
        config['MARKOV_CHAIN']['accept'] = objectiveFunc.get()

    # CONFIGFILE OUTPUT NAME
    cFileName = cfilename.get()
    cFileName = cFileName.split(".")[0] + ".ini"
    top.destroy()


top = tk.Tk()


top.title("make a config file & run chain!")
top.geometry("x".join([str(x) for x in windowSize]))

# top bar of the window is for grpah import/setup
GRAPH = tk.Frame(top, bg=col2)
GRAPH.place(x=0, y=0, relheight=1 / 3, relwidth=1)
graphtitle = tk.Label(GRAPH, anchor="w",
        text="SELECT GRAPH / GEOGRAPHY FILE",
        font="Helvetica 14", fg=col1, bg=col2)
graphtitle.place(relx=offset, rely=offset, relwidth=1, relheight=0.15)
GRAPHINPUT = tk.Frame(GRAPH, bg=col2)
GRAPHINPUT.place(relx=2 * offset, rely=0.2, relwidth=1, relheight=0.45)


def getGraphSource():
    global gSource
    gSource = filedialog.askopenfilename()
    gsource.config(text=gSource[-10:])


def getDataSource():
    global vSource
    vSource = filedialog.askopenfilename()
    vsource.config(text='...' + vSource[-10:])


def clear_idprompt(event):
    gid.delete(0, tk.END)


def clear_popprompt(event):
    gpop.delete(0, tk.END)


def clear_areaprompt(event):
    garea.delete(0, tk.END)


def clear_cdprompt(event):
    gcd.delete(0, tk.END)


def clear_vidprompt(event):
    vid.delete(0, tk.END)


def clear_vdataprompt(event):
    vdata.delete(0, tk.END)


def updateEvalF():
    global columns, columnNameChoices, evalOptions
    if vSource != '':
        if vSource.split('.')[-1] == 'shp' or vSource.split('.')[-1] == 'dbf':
            columns = gp.read_file(vSource).columns
        elif vSource.split('.')[-1] == 'xlsx':
            columns = pd.read_excel(vSource).columns
        elif vSource.split('.')[-1] == "csv":
            columns = pd.read_csv(vSource).columns
        else:
            raise Exception("ERROR: vote data file type not supported")

        colnamemenu.configure(state='normal')
        for item in evalOptions:
            score_menu.delete(item)
            menu = tk.Menu(score_menu, tearoff=False)
            score_menu.add_cascade(label=item, menu=menu)

            columnNameChoices[item] = {}
            for value in columns:
                columnNameChoices[item][value] = tk.BooleanVar(value=False)
                menu.add_checkbutton(label=value,
                        variable=columnNameChoices[item][value],
                        onvalue=True, offvalue=False, command=add_to_evallist)


gsource = tk.Button(GRAPHINPUT, text="Browse", command=getGraphSource, width=10)
gsource.place(relx=2 * offset, rely=0)
gid = tk.Entry(GRAPHINPUT, width=10)
gid.bind("<Button-1>", clear_idprompt)
gid.insert(tk.END, "ID")
gid.place(relx=2 * offset + 0.2, rely=0)
gpop = tk.Entry(GRAPHINPUT, width=10)
gpop.insert(tk.END, "Population")
gpop.bind("<Button-1>", clear_popprompt)
gpop.place(relx=2 * offset + 0.4, rely=0)
garea = tk.Entry(GRAPHINPUT, width=10)
garea.insert(tk.END, "Area")
garea.bind("<Button-1>", clear_areaprompt)
garea.place(relx=2 * offset + 0.6, rely=0)
gcd = tk.Entry(GRAPHINPUT, width=10)
gcd.insert(tk.END, "CD")
gcd.bind("<Button-1>", clear_cdprompt)
gcd.place(relx=2 * offset + 0.8, rely=0)


VOTESOURCE = tk.Frame(GRAPH, bg=col2)
VOTESOURCE.place(relx=2 * offset, rely=0.5, relwidth=1, relheight=0.65)


def enable_voting_data():
    if gcsvvar.get():
        vsource.configure(state='normal')
        vid.configure(state='normal')
        vdata.configure(state='normal')
    elif gcsvvar.get():
        vsource.configure(state='disabled')
        vid.configure(state='disabled')
        vdata.configure(state='disabled')


gcsvvar = tk.BooleanVar()
gcsv = tk.Checkbutton(VOTESOURCE,
        text="(OPTIONAL) ADD VOTE DATA",
        variable=gcsvvar,
        bg=col2,
        fg=col1,
        onvalue=True,
        offvalue=False,
        command=enable_voting_data)
gcsv.place(relx=0, rely=0)

vsource = tk.Button(VOTESOURCE, text="Browse", command=getDataSource, width=10)
vsource.place(relx=2 * offset, rely=0.35)
vsource.configure(state='disabled')
vid = tk.Entry(VOTESOURCE, width=10)
vid.bind("<Button-1>", clear_vidprompt)
vid.insert(tk.END, "ID")
vid.place(relx=2 * offset + 0.2, rely=0.35)
vid.configure(state='disabled')
vdata = tk.Entry(VOTESOURCE, width=42)
vdata.insert(tk.END, "names of columns to add, comma separated")
vdata.bind("<Button-1>", clear_vdataprompt)
vdata.place(relx=2 * offset + 0.4, rely=0.35)
vdata.configure(state='disabled')

SCORING = tk.Frame(top, bg=col1)
SCORING.place(relx=0, rely=1 / 3, relwidth=1, relheight=2 / 3)


def clear_numstepsdata(event):
    numstepsdata.delete(0, tk.END)


def clear_proposaldata(event):
    proposaldata.delete(0, tk.END)


def add_to_validlist(event):
    global vfuncs
    newfunc = validvar.get()
    if (newfunc not in vfuncs) and (newfunc != "VALIDATORS"):
        validlist.configure(state="normal")
        validlist.insert(tk.END, str(newfunc) + ",")
        validlist.configure(state="disabled")
        vfuncs.append(newfunc)


def add_to_evallist():
    global efuncs
    keysOfInterest = [x for x in columnNameChoices if any(
        [y.get() for y in columnNameChoices[x].values()])]

    allfuncs = [x + ',' + ','.join(y for y, z
            in columnNameChoices[x].items() if z.get())
            for x in keysOfInterest]
    evallist.configure(state="normal")
    evallist.delete(0, tk.END)
    evallist.insert(0, ';'.join(allfuncs))
    evallist.configure(state="disabled")
    efuncs = [x for x in allfuncs]


def select_prop_method(event):
    pass


def select_vis_type():
    global vchoices
    if vchoices["histogram"].get():
        box1.configure(state='normal')
    else:
        box1.configure(state='normal')
        box1.delete(0, tk.END)
        box1.insert(0, "plot filename")
        box1.configure(state='disabled')

    if vchoices["save_history_of_changes"].get():
        box2.configure(state='normal')
    else:
        box2.configure(state='normal')
        box2.delete(0, tk.END)
        box2.insert(0, "json filename")
        box2.configure(state='disabled')

    if vchoices["p_value"].get():
        box3.configure(state='normal')
    else:
        box3.configure(state='normal')
        box3.delete(0, tk.END)
        box3.insert(0, "report filename")
        box3.configure(state='disabled')


def toggle_valid_edit():
    validlist.config(state="normal")


def clear_cfilenameprompt(event):
    cfilename.delete(0, tk.END)


def clear_box1(event):
    box1.delete(0, tk.END)


def clear_box2(event):
    box2.delete(0, tk.END)


def clear_box3(event):
    box3.delete(0, tk.END)


markovconfig = tk.Label(SCORING, anchor="w", text="MARKOV CHAIN CONSTRAINTS", fg=col2)
markovconfig.place(relx=offset, rely=offset, relwidth=1, relheight=0.1)

PROPF = tk.Frame(SCORING)
PROPF.place(relx=offset, rely=.1 + offset, relwidth=1 - 2 * offset, relheight=.1)
propvar = tk.StringVar(value="Proposal Type")
proposaldata = tk.OptionMenu(PROPF, propvar, *propOptions,
        command=select_prop_method)
proposaldata.config(width=20)
proposaldata.place(relx=offset, rely=0, relheight=1)
numstepsdata = tk.Entry(PROPF, width=25)
numstepsdata.insert(tk.END, "Number of steps to run")
numstepsdata.bind("<Button-1>", clear_numstepsdata)
numstepsdata.place(relx=0.3 + offset, rely=0, relheight=1)

VALIDF = tk.Frame(SCORING)
VALIDF.place(relx=offset, rely=.25 + offset, relwidth=1 - 2 * offset, relheight=.1)
validvar = tk.StringVar(value="Constraints")
validators = tk.OptionMenu(VALIDF, validvar, *validOptions, command=add_to_validlist)
validators.config(width=20)
validators.place(relx=offset, rely=0, relheight=1)
validlist = tk.Entry(VALIDF, width=45)
validlist.place(relx=0.3 + offset, rely=0, relheight=1)

validEditable = tk.BooleanVar(value=False)
validEditToggle = tk.Checkbutton(VALIDF, text="edit", variable=validEditable,
        onvalue=True, offvalue=False, command=toggle_valid_edit)
validEditToggle.place(relx=0.9, rely=0)


EVALF = tk.Frame(SCORING)
EVALF.place(relx=offset, rely=.4 + offset, relwidth=1 - 2 * offset, relheight=.1)
evalvar = tk.StringVar(value="Scores to Evaluate")

colnamemenu = tk.Menubutton(EVALF, textvariable=evalvar, indicatoron=True, width=20)
score_menu = tk.Menu(colnamemenu, tearoff=False)
colnamemenu.configure(menu=score_menu)

for item in evalOptions:
    menu = tk.Menu(score_menu, tearoff=False)
    score_menu.add_cascade(label=item, menu=menu)

colnamemenu.place(relx=offset, rely=0, relheight=1)
colnamemenu.bind(add_to_evallist)
colnamemenu.configure(state='disabled')
updateMenu = tk.Button(EVALF, text="enable", command=updateEvalF, height=1, width=5)

evallist = tk.Entry(EVALF, width=45)
evallist.place(relx=.3 + offset, rely=0, relheight=1)
updateMenu.place(relx=0.9, rely=0, relheight=1)

OUTPUTSF = tk.Frame(SCORING)
OUTPUTSF.place(relx=offset, rely=.55 + offset, relwidth=1 - 2 * offset, relheight=.1)


visdatatype = tk.StringVar(value="Visualization")
vchoices = {}
mychoice = tk.Menubutton(OUTPUTSF, textvariable=visdatatype, indicatoron=True)
vischoice = tk.Menu(mychoice, tearoff=False)
mychoice.configure(width=20, menu=vischoice)

for key, item in visOptions.items():
    vchoices[key] = tk.BooleanVar(False)
    menu = tk.Menu(vischoice, tearoff=False)
    vischoice.add_checkbutton(label=item, variable=vchoices[key],
            onvalue=True, offvalue=False, command=select_vis_type)


mychoice.configure(width=20, menu=vischoice)
mychoice.place(relx=offset, rely=0)

box1 = tk.Entry(OUTPUTSF, width=12)
box2 = tk.Entry(OUTPUTSF, width=12)
box3 = tk.Entry(OUTPUTSF, width=12)
box1.insert(0, "plot filename")
box2.insert(0, "json filename")
box3.insert(0, "report filename")
box1.bind("<Button-1>", clear_box1)
box2.bind("<Button-1>", clear_box2)
box3.bind("<Button-1>", clear_box3)
box1.place(relx=.3 + offset, rely=0)
box3.place(relx=.5 + offset, rely=0)
box2.place(relx=.7 + offset, rely=0)


ACCEPTF = tk.Frame(SCORING)
ACCEPTF.place(relx=offset, rely=.7 + offset, relwidth=1 - 2 * offset, relheight=.1)
objectiveFunc = tk.StringVar(value="Acceptance Function")
objectiveFuncs = tk.OptionMenu(ACCEPTF, objectiveFunc, "always_accept")
objectiveFuncs.config(width=20)
objectiveFuncs.place(relx=offset, rely=0)


OUTPUTF = tk.Frame(SCORING, bg=col2)
OUTPUTF.place(relx=0, rely=.8 + offset, relwidth=1, relheight=.2)
cfilename = tk.Entry(OUTPUTF, width=20)
cfilename.insert(tk.END, "config file name")
cfilename.bind("<Button-1>", clear_cfilenameprompt)
cfilename.place(relx=2 * offset, rely=.25)

b = tk.Button(OUTPUTF, text="create config file", width=20, command=callback)
b.place(relx=.72, rely=.25)


top.mainloop()


if cFileName != "":
    with open(cFileName, 'w') as configfile:
        config.write(configfile)
    print("Success!!\nto use, type ''python __main__.py %s '' into terminal" % cFileName)
