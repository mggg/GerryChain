from tkinter import *

windowSize = [615, 325]
top = Tk()
top.geometry("615x325")
top.title('Markov Chains!')

basicFileName = ''
basicGeoid = ''
basicPop = ''
basicArea = ''
basicCD = ''
dataFile = ''
dataGeoid = ''
dataPop = ''
validators_list = ''
scores_list = ''
propRandomFlip = ''
numberOfSteps = ''
always_accept = ''
score_logger = ''
visualizations = ''
output = ''


def callback():
    '''
    Main function of the Process button to pull out the text entry fields.
    :return: Strings of all the column names specified.
    '''
    global basicFileName, basicGeoid, basicPop, basicArea, basicCD, dataFile, \
      dataGeoid, dataPop, validators_list, \
      scores_list, propRandomFlip, numberOfSteps, always_accept, \
      score_logger, visualizations, output
    basicFileName = basicFN.get()
    basicGeoid = geoid1.get()
    basicPop = popID1.get()
    basicArea = areaIn.get()
    basicCD = cdIn.get()
    dataFile = dataFN.get()
    dataGeoid = geoid2.get()
    dataPop = popID2.get()
    validators_list = validTextEntry.get()
    scores_list = scoresTextEntry.get()
    propRandomFlip = proposeRandomFlip.get()
    numberOfSteps = numOfSteps.get()
    always_accept = alwaysAccept.get()
    score_logger = scoreLogger.get()
    visualizations = vis.get()
    output = outPutFileName.get()
    top.destroy()


basicFN = Entry(top, width=25)
basicFN.insert(END, 'Basic File Name')
basicFN.pack()
basicFN.place(relx=10./windowSize[0], rely=10./windowSize[1])

dataFN = Entry(top, width=25)
dataFN.insert(END, 'Data File Name')
dataFN.pack()
dataFN.place(relx=200./windowSize[0], rely=10./windowSize[1])

geoid1 = Entry(top, width=10)
geoid1.insert(END, 'GEOID')
geoid1.pack()
geoid1.place(relx=10./windowSize[0], rely=35./windowSize[1])

geoid2 = Entry(top, width=10)
geoid2.insert(END, 'GEOID')
geoid2.pack()
geoid2.place(relx=200./windowSize[0], rely=35./windowSize[1])

popID1 = Entry(top, width=10)
popID1.insert(END, 'POP')
popID1.pack()
popID1.place(relx=100./windowSize[0], rely=35./windowSize[1])

popID2 = Entry(top, width=10)
popID2.insert(END, 'POP')
popID2.pack()
popID2.place(relx=290./windowSize[0], rely=35./windowSize[1])

areaIn = Entry(top, width=10)
areaIn.insert(END, 'AREA')
areaIn.pack()
areaIn.place(relx=10./windowSize[0], rely=60./windowSize[1])

cdIn = Entry(top, width=10)
cdIn.insert(END, 'CD')
cdIn.pack()
cdIn.place(relx=100./windowSize[0], rely=60./windowSize[1])


OPTIONS1 = [
  "VALIDATORS",
  "L1_reciprocal_polsby_popper",
  "within_percent_of_ideal_population",
  "single_flip_contiguous",
  "contiguous",
  "fast_connected",
  "districts_within_tolerance",
  "refuse_new_splits",
  "no_vanishing_districts"
]
var1 = StringVar(top)
var1.set(OPTIONS1[0])
validators = OptionMenu(top, var1, *OPTIONS1)
validators.config(width=20)
validators.pack()
validators.place(relx=5./windowSize[0], rely=80./windowSize[1])

validTextEntry = Entry(top, width=60)
validTextEntry.insert(END, 'Comma separated validators')
validTextEntry.pack()
validTextEntry.place(relx=175./windowSize[0], rely=85./windowSize[1])

OPTIONS2 = [
  "SCORES",
  "efficiency_gap",
  "mean_median",
  "mean_thirdian",
  "L1_reciprocal_polsby_popper",
  "normalized_efficiency_gap",
  "perimeters",
  "polsby-popper",
  "p_value"
]
var2 = StringVar(top)
var2.set(OPTIONS2[0])
updaters = OptionMenu(top, var2, *OPTIONS2)
updaters.config(width=20)
updaters.pack()
updaters.place(relx=5./windowSize[0], rely=115./windowSize[1])

scoresTextEntry = Entry(top, width=60)
scoresTextEntry.insert(END, 'Comma separated scores with columns, then semicolons')
scoresTextEntry.pack()
scoresTextEntry.place(relx=175./windowSize[0], rely=120./windowSize[1])

proposeRandomFlip = Entry(top, width=50)
proposeRandomFlip.insert(END, 'Proppose Random Flip')
proposeRandomFlip.pack()
proposeRandomFlip.place(relx=10./windowSize[0], rely=160./windowSize[1])

numOfSteps = Entry(top, width=20)
numOfSteps.insert(END, 'Number of steps')
numOfSteps.pack()
numOfSteps.place(relx=320./windowSize[0], rely=160./windowSize[1])

alwaysAccept = Entry(top, width=24)
alwaysAccept.insert(END, 'Always Accept')
alwaysAccept.pack()
alwaysAccept.place(relx=10./windowSize[0], rely=200./windowSize[1])

scoreLogger = Entry(top, width=24)
scoreLogger.insert(END, 'Score Logger')
scoreLogger.pack()
scoreLogger.place(relx=166./windowSize[0], rely=200./windowSize[1])

vis = Entry(top, width=24)
vis.insert(END, 'Visualizations')
vis.pack()
vis.place(relx=10./windowSize[0], rely=240./windowSize[1])

outPutFileName = Entry(top, width=24)
outPutFileName.insert(END, 'Output File Name')
outPutFileName.pack()
outPutFileName.place(relx=166./windowSize[0], rely=240./windowSize[1])

b = Button(top, text="Process", width=10, command=callback)
b.pack()
b.place(relx=366./windowSize[0], rely=235./windowSize[1])

top.configure(background='blue')
top.mainloop()

print(basicFileName)
print(basicGeoid)
print(basicPop)
print(basicArea)
print(basicCD)
print(dataFile)
print(dataGeoid)
print(dataPop)
print(validators_list)
print(scores_list)
print(propRandomFlip)
print(numberOfSteps)
print(always_accept)
print(score_logger)
print(visualizations)
print(output)
