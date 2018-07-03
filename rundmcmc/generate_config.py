import tkinter as tk
from tkinter import filedialog
import configparser

# GLOBAL WINDOW OPTIONS
col1 = "white"
col2 = "#B0E0E6"
windowSize = [750, 425]

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
    "single_flip_contiguous",
    "contiguous",
    "fast_connected",
    "districts_within_tolerance",
    "refuse_new_splits",
    "no_vanishing_districts"
]
evalOptions = [
    "flips",
    "efficiency_gap",
    "mean_median",
    "mean_thirdian",
    "L1_reciprocal_polsby_popper",
    "normalized_efficiency_gap",
    "perimeters",
    "polsby-popper",
    "p_value"
]
propOptions = [
    "propose_random_flip"
]
visOptions = [
    "histogram",
    "history_as_json",
    "save_to_file"
]


def callback():
    """
    Main function of the Process button to pull out the text entry fields.
    :return: Strings of all the column names specified.
    """
    global cFileName, config, gSource, vSource, gcsvvar, num_steps, proposal, vfuncs, vistype

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
    config['EVALUATION_SCORES_DATA'] = {}

    # TODO: standardize scoring types and outputs
    config["EVALUATION_SCORES_DATA"]["evalScoreLogType"] = "histograms"
    if vistype is not "":
        config['EVALUATION_SCORES_DATA']["vistype"] = str(vistype)
    if saveFileName.get() is not "":
        config['EVALUATION_SCORES_DATA']["savefilename"] = saveFileName.get()

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


# create the window
top = tk.Tk()
top.title("make a config file & run chain!")
top.geometry("x".join([str(x) for x in windowSize]))

# top bar of the window is for grpah import/setup
GRAPH = tk.Frame(top, height=int(2 * windowSize[1] / 8), width=windowSize[0], bg=col2)


w = tk.Label(GRAPH,
        anchor="w",
        text="Select graph/geography file and relevant column names",
        bg=col2,
        fg=col1)
graphx = 0.01


def getGraphSource():
    global gSource
    gSource = filedialog.askopenfilename()
    gsource.config(text='...' + gSource[-5:])


def getDataSource():
    global vSource
    vSource = filedialog.askopenfilename()
    vsource.config(text='...' + vSource[-5:])


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


gsource = tk.Button(GRAPH, text="Browse", command=getGraphSource, width=8)
gsource.place(relx=graphx, rely=0.2)
gid = tk.Entry(GRAPH, width=10)
gid.bind("<Button-1>", clear_idprompt)
gid.insert(tk.END, "ID")
gpop = tk.Entry(GRAPH, width=10)
gpop.insert(tk.END, "Population")
gpop.bind("<Button-1>", clear_popprompt)
garea = tk.Entry(GRAPH, width=10)
garea.insert(tk.END, "Area")
garea.bind("<Button-1>", clear_areaprompt)
gcd = tk.Entry(GRAPH, width=10)
gcd.insert(tk.END, "CD")
gcd.bind("<Button-1>", clear_cdprompt)

gcsvvar = tk.IntVar()
gcsv = tk.Checkbutton(GRAPH,
        text="(optional) add vote data",
        variable=gcsvvar,
        bg=col2,
        fg=col1,
        onvalue=1,
        offvalue=0)
vsource = tk.Button(GRAPH, text="Browse", command=getDataSource, width=8)
vid = tk.Entry(GRAPH, width=10)
vid.bind("<Button-1>", clear_vidprompt)
vid.insert(tk.END, "ID")
vdata = tk.Entry(GRAPH, width=45)
vdata.insert(tk.END, "names of columns to add, comma separated")
vdata.bind("<Button-1>", clear_vdataprompt)
bottomstrip = tk.Label(GRAPH, text="", bg=col2, fg=col1)
xsp = 27
ysp = 1
w.grid(row=0, column=0, columnspan=3, in_=GRAPH, sticky=tk.W, padx=3)
gsource.grid(row=1, column=0, padx=xsp, pady=ysp, sticky=tk.W, in_=GRAPH)
gid.grid(row=1, column=1, padx=xsp, pady=ysp, sticky=tk.W, in_=GRAPH)
gpop.grid(row=1, column=2, padx=xsp, pady=ysp, sticky=tk.W, in_=GRAPH)
garea.grid(row=1, column=3, padx=xsp, pady=ysp, sticky=tk.W, in_=GRAPH)
gcd.grid(row=1, column=4, padx=xsp, pady=ysp, sticky=tk.W, in_=GRAPH)
gcsv.grid(row=2, column=0, columnspan=10, pady=2 * ysp, sticky=tk.W, in_=GRAPH)
vsource.grid(row=3, column=0, padx=xsp, pady=ysp, sticky=tk.W, in_=GRAPH)
vid.grid(row=3, column=1, padx=xsp, pady=ysp, sticky=tk.W, in_=GRAPH)
vdata.grid(row=3, column=2, columnspan=8, padx=xsp, pady=ysp, sticky=tk.W, in_=GRAPH)
bottomstrip.grid(row=4, column=0, columnspan=11)
GRAPH.pack()

# scoring/validity functions and markovchain options
SCORING = tk.Frame(top, height=int(5 * windowSize[1] / 9), width=windowSize[0], bg=col1)


def clear_numstepsdata(event):
    numstepsdata.delete(0, tk.END)


def clear_proposaldata(event):
    proposaldata.delete(0, tk.END)


def add_to_validlist(event):
    newfunc = validvar.get()
    if (newfunc not in vfuncs) and (newfunc != "VALIDATORS"):
        validlist.insert(tk.END, str(newfunc) + ",")
        vfuncs.append(newfunc)


def add_to_evallist(event):
    newfunc = evalvar.get()
    if (newfunc not in efuncs) and (newfunc != "SCORES"):
        evallist.insert(tk.END, str(newfunc) + ",")
        efuncs.append(newfunc)


def select_prop_method(event):
    pass


def select_vis_type(event):
    global vistype
    var = visdatatype.get()
    if not var == "Visualization":
        vistype = var


w = tk.Label(SCORING,
        anchor="w",
        text="Configure MarkovChain constraints",
        bg=col1,
        fg=col2,
        pady=3)
validvar = tk.StringVar(value="Validity Functions")
validators = tk.OptionMenu(SCORING, validvar, *validOptions, command=add_to_validlist)
validators.config(width=20)
validlist = tk.Entry(SCORING, width=55)
evalvar = tk.StringVar(value="Scores to Evaluate")
evals = tk.OptionMenu(SCORING, evalvar, *evalOptions, command=add_to_evallist)
evals.config(width=20)
evallist = tk.Entry(SCORING, width=55)
propvar = tk.StringVar(value="Proposal Type")
proposaldata = tk.OptionMenu(SCORING, propvar, *propOptions, command=select_prop_method)
proposaldata.config(width=20)
numstepsdata = tk.Entry(SCORING, width=25)
numstepsdata.insert(tk.END, "Number of steps to run in chain")
numstepsdata.bind("<Button-1>", clear_numstepsdata)
visdatatype = tk.StringVar(value="Visualization")
vischoice = tk.OptionMenu(SCORING, visdatatype, *visOptions, command=select_vis_type)
vischoice.config(width=20)
objectiveFunc = tk.StringVar(value="Objective Function")
objectiveFuncs = tk.OptionMenu(SCORING, objectiveFunc, "always_accept")
objectiveFuncs.config(width=20)

bysp = 6
w.grid(row=0, column=0, columnspan=3, in_=SCORING, sticky=tk.W, padx=3, pady=2)
proposaldata.grid(row=1, column=1, in_=SCORING, sticky=tk.W, pady=bysp)
validators.grid(row=2, column=1, in_=SCORING, sticky=tk.W, pady=bysp)
validlist.grid(row=2, column=2, columnspan=2, in_=SCORING, sticky=tk.W, pady=bysp)
evals.grid(row=3, column=1, in_=SCORING, sticky=tk.W, pady=bysp)
evallist.grid(row=3, column=2, columnspan=2, in_=SCORING, sticky=tk.W, pady=bysp)
vischoice.grid(row=5, column=1, in_=SCORING, sticky=tk.W, pady=bysp)
objectiveFuncs.grid(row=5, column=2, in_=SCORING, pady=bysp)
numstepsdata.grid(row=5, column=3, in_=SCORING, sticky=tk.E, pady=bysp + 2)
SCORING.pack()

# output file options
OUTPUT = tk.Frame(top, height=int(2 * windowSize[1] / 8), width=windowSize[0], bg=col2)


def clear_cfilenameprompt(event):
    cfilename.delete(0, tk.END)


def clear_saveFileName(event):
    saveFileName.delete(0, tk.END)


outputcommand = tk.Label(OUTPUT, text="config file and chain run output options", bg=col2, fg=col1)
saveFileName = tk.Entry(OUTPUT, width=20)
cfilename = tk.Entry(OUTPUT, width=20)
saveFileName.insert(tk.END, "chain output file name")
saveFileName.bind("<Button-1>", clear_saveFileName)
cfilename.insert(tk.END, "config file name")
cfilename.bind("<Button-1>", clear_cfilenameprompt)
midbar1 = tk.Label(OUTPUT, text="      ", bg=col2, fg=col1)
midbar2 = tk.Label(OUTPUT, text="           ", bg=col2, fg=col1)
midbar3 = tk.Label(OUTPUT, text="           ", bg=col2, fg=col1)
midbar4 = tk.Label(OUTPUT, text="           ", bg=col2, fg=col1)
lastbar = tk.Label(OUTPUT, text="                                        ", bg=col2, fg=col1)

b = tk.Button(OUTPUT, text="create config file", width=20, command=callback)
outputcommand.grid(row=0, column=0, columnspan=4, in_=OUTPUT, padx=10, pady=10, sticky=tk.W)

midbar1.grid(row=2, column=0, in_=OUTPUT)
cfilename.grid(row=2, column=1, in_=OUTPUT, pady=2, sticky=tk.W)
midbar2.grid(row=2, column=2, in_=OUTPUT)
saveFileName.grid(row=2, column=3, in_=OUTPUT, padx=2, pady=2, sticky=tk.W)
midbar3.grid(row=2, column=4, in_=OUTPUT)
b.grid(row=2, column=5, in_=OUTPUT, padx=2, pady=2, sticky=tk.E)
midbar4.grid(row=2, column=6, in_=OUTPUT)
lastbar.grid(row=3, column=0, columnspan=2, sticky=tk.E + tk.W)

OUTPUT.pack()

top.mainloop()
if cFileName != "":
    with open(cFileName, 'w') as configfile:
        config.write(configfile)
    print("Success!!\nto use, type ''python __main__.py %s '' into terminal" % cFileName)
