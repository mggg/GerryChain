from tree_methods import tree_part2

def recursive_bi_part(graph, parts, pop_col, epsilon,node_repeats=1,):
    '''Wrapper for the bipartitioning methods
	returns an assignment dictionary for gerrychain'''
    newlabels={}
    pop_target=0
    for node in graph.nodes():
        pop_target+=graph.nodes[node][pop_col]
    pop_target=pop_target/parts
    
    remaining_nodes=list(graph.nodes())
    for n in newlabels.keys():
        remaining_nodes.remove(n)
    sgraph=nx.subgraph(graph,remaining_nodes)
    
    for i in range(parts-1):
        update=tree_part2(sgraph, pop_col, pop_target, epsilon,node_repeats)
        #update = minflow_part(sgraph, pop_col, pop_target, epsilon)
        #update =  edge_removal_part(sgraph, pop_col, pop_target, epsilon) # inefficient
        for x in list(update[1]):
            newlabels[x]=i
        #update pop_target?
        remaining_nodes=list(graph.nodes())
        for n in newlabels.keys():
            remaining_nodes.remove(n)
        
        sgraph=nx.subgraph(graph,remaining_nodes)
        #print("Built District #", i)
        
    td=set(newlabels.keys())
    for nh in graph.nodes():
        if nh not in td:
            newlabels[nh]=parts-1#was +1 for initial testing
    return newlabels



##### Bipartitioning methods

def minflow_part(graph, pop_col, pop_target, epsilon):
    '''Partitions using a minflow algorithm on random weights'''
    
    
    while 1==1:
        
        w=graph.copy()
        for ed in w.edges():
            w.add_edge(ed[0],ed[1],capacity=random.random())
            
            
        
        start = random.choice(list(w.nodes()))
        end = random.choice(list(w.nodes()))
        ##print(len(list(graph.neighbors(start))))
        ##print(len(list(graph.neighbors(end))))
        pstart= nx.shortest_path_length(graph,source=start)
        pend=nx.shortest_path_length(graph,source=end)
        
        for ed in graph.edges():
            wt=-4
            dmax=max(pstart[ed[0]],pstart[ed[1]],pend[ed[0]],pend[ed[1]])
            dmin=min(pstart[ed[0]],pstart[ed[1]],pend[ed[0]],pend[ed[1]])
            wt = 10**(-(dmin-3)+random.random()) 
            w.add_edge(ed[0],ed[1],capacity=random.gauss(wt,wt/100))
        
                
            
        

            

        val,P = nx.minimum_cut(w, start,end,capacity='capacity')
        
        
        path = list(nx.shortest_path(graph,source=start,target=end))

        clusters={}
        clusters[1]=P[0]
        clusters[-1]=P[1]
        clusters[2] = [start]
        clusters[3] =[end]     
        path.remove(start)
        path.remove(end)
        clusters[4]=path
        tsum =0
        for n in P[0]:
            tsum+=graph.nodes[n][pop_col]
        #print(tsum/pop_target)
        if abs(tsum-pop_target) < epsilon*pop_target:
            return clusters
			
			
			
         
def edge_removal_part(graph, pop_col, pop_target, epsilon):
    
    w=graph.copy()
    wlist=[x for x in range(10)]
    temp=0
    while 1==1:
        e = random.choice(list(w.edges()))
        w.remove_edge(e[0],e[1])
        
        if not nx.is_connected(w):
            cc=list(nx.connected_components(w))
            tsums=[]
            for l in cc:
                tsums.append(0)
                for n in l:
                    ##print(removed)
                    tsums[-1]=tsums[-1]+graph.nodes[n][pop_col]
            
            val, idx = min((val, idx) for (idx, val) in enumerate(tsums))
            #print(len(list(w.edges())),val/pop_target)
            wlist[temp]=len(list(w.edges()))
            temp+=1
            temp=temp%10
            if abs(val -pop_target) < epsilon*pop_target:
                l=cc[idx]
                clusters={}
                clusters[1]=list(l)
                clusters[-1]=[]

                for n in graph.nodes():
                    if n not in l:
                        clusters[-1].append(n)
                return clusters
            else:
                w.add_edge(e[0],e[1])
                if len(set(wlist))==1:
                    w=graph.copy()
