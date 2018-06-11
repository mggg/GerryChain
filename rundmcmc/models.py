import networkx


def _construct_graph_from_lists_of_neighbors(lists_of_neighbors, lists_of_perims):
    graph = networkx.Graph()
    node_ids = list(range(len(lists_of_neighbors)))
    graph.add_nodes_from(node_ids)
    for node_id in node_ids:
        nbs = lists_of_neighbors[node_id].split(',')
        pms = lists_of_perims[node_id].split()
        for edge_idx, edge in enumerate(nbs):
            graph.add_edge(node_id, edge, shared_perimeter=pms[edge_idx])
    return graph


class AggregateState(object):
    def __init__(self, state_df, *args, **kwargs):
        self._state_df = state_df.copy()
        self._aggregate = state_df.groupby('district').sum()

        # working with the comma-separated strings in the pandas dataframe would be painful.
        #    This reformats the same data into an easier to use format.  The outer dictionary keys
        #    are just the subunit (precinct) IDs, while the inner dict provides both the neighbors
        #    and shared perimeters, since they are used together.
        self._neighbor_map = {rec['Subunit ID']: {
                                    'nb': [int(nb.strip()) for nb in rec['nb'].split(',')],
                                    'sp': [float(sp.strip()) for sp in rec['sp'.split(',')]],
                              }
                              for rec in state_df}

        self.use_counties = 'county' in self._state_df
        if self.use_counties:
            self.districtCountyPopulations = state_df.groupby(('district', 'county')).sum()['pop']

        # computing these is more annoying because they're variable length lists.  Can't
        #    use pandas groupby aggregation.
        self._perim_pop = None
        self._perim = None
        self._graph = _construct_graph_from_lists_of_neighbors(self._state_df['nb'],
                                                              self._state_df['sp'])

    def _attr(self, attr_name, district_id):
        """facilitate access of data table columns"""
        return (self._aggregate[attr_name][district_id] if district_id is not None else
                self._aggregate[attr_name])

    # attribute viewing

    def area(self, district_id=None):
        '''total perimeters on a per-district basis'''
        #   TODO: probably wrong.  Needs to be something using "SP", I think.
        return self._attr('area', district_id)

    def Ashare(self, district_id=None):
        return self.voteA(district_id) / self.total_votes(district_id)

    def perim(self, district_id=None):
        '''total perimeters on a per-district basis'''
        return (self._perim[district_id] if district_id is not None else self._perim)

    def perim_pop(self, district_id=None):
        """Population in subunits that are along the perimeter of a district"""
        return (self._perim_pop[district_id] if district_id is not None else self._perim_pop)

    def pop(self, district_id=None):
        '''total perimeters on a per-district basis'''
        return self._attr('pop', district_id)

    def total_vote(self, district_id=None):
        '''total votes on a per-district basis'''
        return self._attr('voteA', district_id) + self._attr('voteB', district_id)

    def voteA(self, district_id=None):
        '''total votes for party A on a per-district basis'''
        return self._attr('voteA', district_id)

    def voteB(self, district_id=None):
        '''total votes for party B on a per-district basis'''
        return self._attr('voteB', district_id)

    @property
    def graph_edges(self):
        return self._graph.edges

    # ways to change state

    def reassign_subunit(self, subunit_id, neighbor_subunit_id):
        """Modify state in place to reassign neighbor subunit into current subunit's district

        This function is a refactor of the "chainstep" function from the CFP code."""
        subunit_record = self._state_df.loc[subunit_id]
        current_district = subunit_record['district']
        neighbor_record = self._state_df.loc[neighbor_subunit_id]
        neighbor_district = neighbor_record['district']

        if current_district == neighbor_district:
            raise ValueError("For subunits {} and {}, district is same.  Can't swap.  Exiting")

        # carryover from c++; not sure how this could actually happen
        if neighbor_district < 0:
            raise ValueError("Tried to add outside of district")

        for attr in 'voteA', 'voteB', 'pop', 'area':
            self._aggregate[current_district][attr] += neighbor_record[attr]
            self._aggregate[neighbor_district][attr] -= neighbor_record[attr]

        if self.use_counties:
            self.districtCountyPopulations[current_district][neighbor_record.county] += neighbor_record.pop
            self.districtCountyPopulations[neighbor_district][neighbor_record.county] -= neighbor_record.pop

        # check current assignment of each neighbor; adjust perimeters and populations accordingly
        neighbors = self.neighbors_map[neighbor_subunit_id]
        # neighbor here is actually neighbor's neighbor
        for neighbor, sp_change in zip(neighbors['nb'], neighbors['sp']):
            # outside edge
            if neighbor < 0:
                self._perim[current_district] += sp_change  # because it avoids Du
                self._perim_pop[current_district] += neighbor_record.pop
                self._perim[neighbor_district] -= sp_change  # because it avoids Dv
                self._perim_pop[neighbor_district] -= neighbor_record.pop

            elif self._state_df.loc[neighbor].district == current_district:
                if not neighbor_record.frozen:
                    # Really not sure about this.  Old code is hard to understand what's going on.
                    #
                    # v is the neighbor id
                    # int v = pr[e.u].neighbors[e.j];
                    #
                    # loop over each neighbor.  l is integer index of neighbor, not neighbor id.
                    # for (int l = 0; l < pr[v].degree; l++)
                    #
                    # Why do we have an edge between the neighbor id (v)
                    # edgeset.remove(edge(v, l));
                    #
                    # edge to remove is (neighbor's neighbor [loop idx],
                    #                    neighbor inverse neighbor map [loop idx])
                    #    that seems incredibly roundabout.  Is there a simpler description?
                    # edgeset.remove(edge(pr[v].neighbors[l], pr[v].self[l]));
                    #
                    # I have gone with the assumption that we want to break (or make) edges between
                    # the neighbor and its neighbors
                    #
                    self._graph.remove_edge(neighbor_subunit_id, neighbor)
                    self._graph.remove_edge(neighbor, neighbor_subunit_id)
                self._perim[current_district] += sp_change  # because it avoids Du
                self._perim_pop[current_district] += neighbor_record.pop
                self._perim[neighbor_district] += sp_change  # because it intersects Dv
                self._perim_pop[neighbor_district] += neighbor_record.pop

            elif self._state_df.loc[neighbor].district == neighbor_district:
                if not neighbor_record.frozen:
                    self._graph.insert_edge(neighbor_subunit_id, neighbor,
                                            shared_perimeter=sp_change)
                    self._graph.insert_edge(neighbor, neighbor_subunit_id,
                                            shared_perimeter=sp_change)
                self._perim[current_district] -= sp_change  # because it avoids Du
                self._perim_pop[current_district] -= neighbor_record.pop
                self._perim[neighbor_district] -= sp_change  # because it intersects Dv
                self._perim_pop[neighbor_district] -= neighbor_record.pop

            else:     # avoids Du AND Dv
                self._perim[current_district] += sp_change  # because it avoids Du
                self._perim_pop[current_district] += neighbor_record.pop
                self._perim[neighbor_district] -= sp_change  # because it avoids Dv
                self._perim_pop[neighbor_district] -= neighbor_record.pop

        neighbor_record['district'] = current_district

    def connectivity_check(self):
        """invalidate a step or initial map if the graph is not well-behaved"""
        pass

    def directionality_check(self):
        """
        for (int i=0; i<N; i++){
            for (int j=0; j<N; j++){
            if (adjM[i][j]!=adjM[j][i]){
        cerr << "ERROR: graph is not undirected!"<< endl;
        cerr << "bad pair is "<<i<<","<<j<<"."<<endl;
        exit(-1);
            }
            }
        }
        """
        pass

    def constraints_check(self, enabled_checks=None):
        """invalidate a step or initial map based on computed values and pre-set thresholds

        Checks themselves are defined as metrics.  enabled_checks should be a dictionary,
        where the keys are the metric function name, and the value is the threshold.  If a
        threshold is not required for a metric, you can pass any dummy value and it will just
        be ignored."""
        enabled_checks = enabled_checks or {}
        pass
