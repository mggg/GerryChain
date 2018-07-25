import matplotlib.pyplot as plt
from rundmcmc.validity import (L1_reciprocal_polsby_popper,
                               L_minus_1_polsby_popper)
from rundmcmc.scores import (efficiency_gap, mean_median,
                             how_many_seats_value,
                             L2_pop_dev)


def write_header_styles(fstream):
    fstream.write("\n<style>\n")
    fstream.write("table { font-family: arial, sans-serif;" + 
                  "border-collapse: collapse; width: 100%; }\n")
    fstream.write("td, th { border: 1px solid #dddddd; text-align: left;" +
                  "padding: 8px; }\n")
    fstream.write("tr:nth-child(even) { background-color: #dddddd; }\n")
    fstream.write("mycolor {#ff0000}\n")
    fstream.write("</style>\n\n")
    

def write_initial_report(newdir, outputName, partition, df_to_plot, state_name,
 district_col, num_elections, election_names, election_columns, df,
                         unique_label, validator):
 
    num_districts = len(partition['cut_edges_by_part'])

    with open(outputName, "w") as f:
        f.write("<html>\n")
        write_header_styles(f)

        f.write("<body>\n")
        f.write("<h1 width:100%>" + state_name + " Initial Report</h1>\n")
        f.write("<h2 width:100%>Initial Data</h2>\n")
        f.write("<b>Initial Districting Plan: </b>")
        f.write(district_col)
        f.write("<br><br><b>Election Data:</b>")
        for i in range(num_elections):
            f.write(election_names[i] + "  ")
                
        df_to_plot.plot(column="initial", cmap='tab20')

        plt.axis('off')
        plt.title(state_name + " Plan: " + district_col)
        plt.savefig(newdir + "initial_CD.png")
        plt.close()

        f.write("<div width=100%>\n")
        f.write(f"    <img src='initial_CD.png' width=80%/>\n")
        f.write("</div>\n")

        f.write("<h2>Statewide Stats</h2>\n\n")
        f.write("<b>Number of Districts: </b> " + str(num_districts) + "<br>")
        f.write("<b>Population Deviation: </b>" + str(L2_pop_dev(partition)) + "<br>")
        f.write("<b>Reciprocal Polsby-Popper L1: </b>" +
                str(L1_reciprocal_polsby_popper(partition)) + "<br>")
        f.write("<b>Polsby-Popper L(-1): </b>" + str(L_minus_1_polsby_popper(partition))
                + "<br>")
        f.write("<b>Conflicted Edges: </b>" + str(len(partition["cut_edges"])) + "<br>")
        f.write("<b>Boundary Nodes: </b>" + str(len(partition["boundary_nodes"])) + "<br>")

        f.write("<h2> Statewide Partisan Measures</h2>")
        f.write("<div width=100%>\n")

        for i in range(num_elections):
                df["Dperc"]=df[election_columns[i][1]] / (df[election_columns[i][0]]+ df[election_columns[i][1]])
        
                df_to_plot["partisan"] = df_to_plot[unique_label].map(df.to_dict()["Dperc"])

                df_to_plot.plot(column ="partisan", cmap="seismic")
                plt.axis('off')
                plt.title(election_names[i] + " Vote Percentage")
                plt.savefig(newdir + "partisan" + str(i)+".png")
                plt.close()
                
                f.write("<img src='partisan" + str(i)+".png' width=40%/>\n")
                
        f.write("</div>\n")

        f.write("<table>\n <tr><td>Election</td><td>D Seats</td><td>R Seats</td><td> D Votes</td><td>R Votes</td>" + 
                "<td>D Percent</td><td> R percent</td><td> Mean Median </td><td> Efficiency Gap</td> </tr>")

        for i in range(num_elections):
                f.write("<tr><td>" + election_names[i] + "</td><td>" +
                        str(how_many_seats_value(partition,election_columns[i][0],
                                                 election_columns[i][1])) + "</td><td>" +
                        str(how_many_seats_value(partition,election_columns[i][1],
                                                 election_columns[i][0])) + "</td><td>" +
                        str(sum(df[election_columns[i][0]])) + "</td><td>" +
                        str(sum(df[election_columns[i][1]])) + "</td><td>" +
                        str(sum(df[election_columns[i][0]])/(sum(
                                df[election_columns[i][0]])+sum(df[election_columns[i][1]])))
                        + "</td><td>" +
                        str(sum(df[election_columns[i][1]])/(sum(
                                df[election_columns[i][0]])+sum(df[election_columns[i][1]])))
                        + "</td><td>" +
                        str(mean_median(partition,election_columns[i][0] + "%")) + "</td><td>" +
                        str(efficiency_gap(partition,election_columns[i][0],election_columns[i][1]))
                        +"</td></tr>")

        f.write("</table>\n\n")

        f.write("<h2> District Partisan Measures</h2>")
        
        win_dict = {0 : "D", 1 : "R"}
        dw_list=[]
        f.write("<div width=100%>\n")

        for i in range(num_elections):
                district_winners={}

                for j in range(num_districts):
                        district_winners[j+1] = int(partition[election_columns[i][1]][j+1]
                                                         > partition[election_columns[i][0]][j+1])

                df_to_plot["district_partisan"] = df_to_plot[district_col].map(district_winners)
                dw_list.append(district_winners)
                
                df_to_plot.plot(column="district_partisan", cmap="seismic")
                plt.axis('off')
                plt.title(election_names[i] + " District Winners")
                plt.savefig(newdir + "district_partisan" + str(i)+ ".png")
                plt.close()

                f.write("<img src='district_partisan" + str(i) + ".png' width=40%/>\n")
        f.write( "</div>\n")

        f.write("<table>\n <tr><td>District</td>")
        for i in range(num_elections):
                f.write("<td>" + election_names[i] + " Winner</td>" +
                        "<td>" + election_names[i] + " Win %</td>")
        f.write("</tr>")

        for i in range(num_districts):
                f.write("<tr><td>" + str(i+1) + "</td>")
                for j in range(num_elections):
                        f.write("<td>" + win_dict[dw_list[j][i+1]] + "</td><td>" +
                                str(partition[election_columns[j][dw_list[j][i+1]] +
                                              "%"][i+1]) +
                                "</td>")
        f.write("</tr></table>")

        f.write("</table>")

        f.write("<h2> District Measures </h2>")

        df_to_plot["PP"] = df_to_plot[district_col].map(partition["polsby_popper"])

        df_to_plot.plot(column="PP", cmap="cool")

        plt.axis("off")
        plt.title("District Polsby-Popper Scores")
        plt.savefig(newdir + "district_PP" + ".png")
        plt.close()

        f.write("<div width=100%>\n")
        f.write(f"    <img src='district_PP.png' width=80%/>\n")
        f.write("</div>\n")

        f.write("<table>\n<td>District</td><td>Units</td><td>Conflicted Edges</td>" +
                "<td>Population Deviation %</td><td>Polsby-Popper</td></tr>")

        number_of_districts = len(partition['population'].keys())
        total_population = sum(partition['population'].values())
        mean_population = total_population / num_districts

        for i in range(num_districts):
                f.write("<tr><td>" + str(i+1) + "</td><td>" +
                        str(len(partition.parts[i+1])) + "</td><td>" +
                        str(len(partition["cut_edges_by_part"][i+1])) + "</td><td>" +
                        str((partition["population"][i+1] - mean_population) / (
                            total_population)) + "</td><td>" +
                        str(partition["polsby_popper"][i+1]) + "</td></tr>")

        f.write("</table>")
