#  -*- coding: utf-8 -*-
"""
Created on Mon Jul 23 10:13:50 2018

@author: tasju
"""

import math


def countyEntropyReport(partition, pop_col="POP100", county_col="COUNTYFP10"):
    weight_opts = [1, -1, 'Infinity']
    function_opts = [.5, .8, 1, "Shannon"]

    county_stuff = []
    entropy = [[0.0 for x in range(len(weight_opts) + 1)] for y in range(len(function_opts) + 1)]
    statePop = 0

    # assign each VTD to county dictionary
    countyDict = {}
    vtdList = partition.graph.nodes

    for vtd1 in vtdList:
        statePop += float(vtdList[vtd1][pop_col])
        countyDict.setdefault(vtdList[vtd1][county_col], [])
        countyDict[vtdList[vtd1][county_col]].append(vtd1)

    # go through each county
    for county in countyDict.keys():
        current_county_data = []
    # list containing [countyID, split boolean, county pop, [subpop1,subpop2...]]
        subpop_list = []

        countyPop = 0
        countyDistrictDict = {}
        countyVTDs = countyDict[county]

        # for each VTD in current county assign to district piece
        for vtd2 in countyVTDs:
            countyPop += float(vtdList[vtd2][pop_col])
            assignment = partition.assignment[vtd2]
            if assignment not in countyDistrictDict:
                countyDistrictDict[assignment] = []

            countyDistrictDict[partition.assignment[vtd2]].append(vtd2)

        # calculate county weights
        countyWeight_list = []
        for weight_exp in weight_opts:
            if weight_exp == "Infinity":
                countyWeight = 1
            else:
                if countyPop > 0:
                    countyWeight = ((countyPop * 1.0) / (statePop * 1.0))**weight_exp
                else:
                    countyWeigt = 0
            countyWeight_list.append(countyWeight)

        # for each district piece in current county
        for intersectionVTDs in countyDistrictDict.values():
            intersectionPop = 0
            for vtd3 in intersectionVTDs:
                intersectionPop += float(vtdList[vtd3][pop_col])

            if countyPop > 0:
                intersectionWeight = (intersectionPop * 1.0) / (countyPop * 1.0)
            else:
                intersectionWeight = 1

            # for each county weight option and each function option calculate entropy
            a = 0
            for countyWeight in countyWeight_list:
                b = 0
                for function in function_opts:
                    if intersectionWeight != 0:
                        if function == "Shannon":
                            entropy[a][b] += countyWeight * intersectionWeight * math.log(
                                                        1.0 / intersectionWeight)
                        else:
                            entropy[a][b] += countyWeight * intersectionWeight * (
                                                        1.0 / intersectionWeight)**(float(function))
                    b += 1
                a += 1
            # record intersection population
            subpop_list.append(intersectionPop)

        # is current county split?
        isSplit = 0
        if len(subpop_list) > 1:
            isSplit = 1

        # record current county data
        current_county_data.append(county)
        current_county_data.append(isSplit)
        current_county_data.append(countyPop)
        current_county_data.append(subpop_list)

        # add current_county_data to state data
        county_stuff.append(current_county_data)

    return [entropy, county_stuff]


def numCountySplit(partition, pop_col="POP100", county_col="COUNTYFP10"):
    numSplit = 0
    countyDict = {}
    countyCodes = []
    vtdList = partition.graph.nodes

    # assign each vtd to county
    for vtd1 in vtdList:
        countyDict.setdefault(vtdList[vtd1][county_col], [])
        countyDict[vtdList[vtd1][county_col]].append(vtd1)

    # go through each county
    for county in countyDict.keys():
        countyVTDs = countyDict[county]

        thisDistrict = partition.assignment[countyVTDs[0]]

        # each vtd in county see if district assignments match
        for vtd2 in countyVTDs:
            assignment = partition.assignment[vtd2]
            if assignment != thisDistrict:
                numSplit = numSplit + 1
                countyCodes.append(county)
                break

    return {'numSplit': numSplit, 'countyCodes': countyCodes}


def countySplitDistrict(partition, pop_col="POP100", county_col="COUNTYFP10"):
    weight_opts = [1, -1, 'Infinity']

    function_opts = [.5, .8, 1, "Shannon"]

    entropy = [[0.0 for x in range(len(weight_opts) + 1)] for y in range(len(function_opts) + 1)]

    statePop = 0

    districtDict = {}

    vtdList = partition.graph.nodes

    for vtd1 in vtdList:

        statePop += float(vtdList[vtd1][pop_col])

        assignment = partition.assignment[vtd1]

        if assignment not in districtDict:

            districtDict[assignment] = []

        districtDict[assignment].append(vtd1)

    for district in districtDict.keys():

        districtPop = 0

        countyDistrictDict = {}
        districtVTDs = districtDict[district]

        for vtd2 in districtVTDs:

            districtPop += float(vtdList[vtd2][pop_col])

            countyDistrictDict.setdefault(vtdList[vtd2][county_col], [])

            countyDistrictDict[vtdList[vtd2][county_col]].append(vtd2)

        districtWeight_list = []

        for weight_exp in weight_opts:

            if weight_exp == "Infinity":

                districtWeight = 1

            else:
                if districtPop > 0:

                    districtWeight = ((districtPop * 1.0) / (statePop * 1.0))**weight_exp
                else:
                    districtWeight = 0

            districtWeight_list.append(districtWeight)

        for intersectionVTDs in countyDistrictDict.values():

            intersectionPop = 0

            for vtd3 in intersectionVTDs:

                intersectionPop += float(vtdList[vtd3][pop_col])

            if districtPop > 0:

                intersectionWeight = (intersectionPop * 1.0) / (districtPop * 1.0)

            else:
                intersectionWeight = 1

            a = 0

            for districtWeight in districtWeight_list:

                b = 0

                for function in function_opts:

                    if intersectionWeight != 0:

                        if function == "Shannon":

                            entropy[a][b] += districtWeight * intersectionWeight * math.log(
                                                        1.0 / intersectionWeight)

                        else:

                            entropy[a][b] += districtWeight * intersectionWeight * (
                                                        1.0 / intersectionWeight)**(float(function))

                    b += 1

                a += 1

    return entropy
