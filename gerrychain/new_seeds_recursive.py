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
			
			
			
def tree_part2(graph, pop_col, pop_target, epsilon,node_repeats):
    '''Partitions by cutting a random spanning tree'''
    
    w=graph.copy()
    for ed in w.edges():
        w.add_edge(ed[0],ed[1],weight=random.random())
    
    T = tree.maximum_spanning_edges(w, algorithm='kruskal', data=False)
    ST= nx.Graph()
    ST.add_edges_from(list(T))
    #nx.draw(ST)
    h=ST.copy()
    
    #nx.draw(ST,layout='tree')
    
    #root = random.choice(list(h.nodes()))
    root = random.choice([x for x in ST.nodes() if ST.degree(x)>1])#this used to be greater than 2 but failed on small grids:(
    ##print(root)
    predbfs=nx.bfs_predecessors(h, root)#was dfs
    pred={}
    for ed in predbfs:
        pred[ed[0]]=ed[1]

    pops={x:[{x},graph.nodes[x][pop_col]] for x in graph.nodes()}
    
    leaves=[]
    t=0
    layer=0
    restarts=0
    while 1==1:
        if restarts==node_repeats:
        
        
            w=graph.copy()
            for ed in w.edges():
                w.add_edge(ed[0],ed[1],weight=random.random())
    
            T = tree.maximum_spanning_edges(w, algorithm='kruskal', data=False)
            ST= nx.Graph()
            ST.add_edges_from(list(T))
            #nx.draw(ST)
            h=ST.copy()
    
        #nx.draw(ST,layout='tree')
    
            #root = random.choice(list(h.nodes()))
            root = random.choice([x for x in ST.nodes() if ST.degree(x)>1])#this used to be greater than 2 but failed on small grids:(
            ##print(root)
            predbfs=nx.bfs_predecessors(h, root)#was dfs
            pred={}
            for ed in predbfs:
                pred[ed[0]]=ed[1]

            pops={x:[{x},graph.nodes[x][pop_col]] for x in graph.nodes()}
    
            leaves=[]
            t=0
            layer=0
            restarts=0
            ##print("Bad tree -- rebuilding")
            
        if len(list(h.nodes()))==1:
            h=ST.copy()
            root = random.choice([x for x in ST.nodes() if ST.degree(x)>1])#this used to be greater than 2 but failed on small grids:(
            ##print(root)
            #pred=nx.bfs_predecessors(h, root)#was dfs
            predbfs=nx.bfs_predecessors(h, root)#was dfs
            pred={}
            for ed in predbfs:
                pred[ed[0]]=ed[1]
            pops={x:[{x},graph.nodes[x][pop_col]] for x in graph.nodes()}
            ##print("bad root --- restarting",restarts)
            restarts+=1
            layer=0
            leaves=[]
            
        if leaves == []:
        
            leaves = [x for x in h.nodes() if h.degree(x)==1]
            layer=layer+1
            
            if len(leaves) == len(list(h.nodes()))-1:
                tsum = pops[root][1]
                for r in range(2,len(leaves)):
                    for s in itertools.combinations(leaves,r):
                        for node in s:
                            tsum+=pops[node][1]
                    if abs(tsum-pop_target)<epsilon*pop_target:
                        #print(pops[leaf][1]/pop_target)
                        clusters={}
                        clusters[1]=list(pops[leaf][0])
                        clusters[-1]=[]
                        for nh in graph.nodes():
                            if nh not in clusters[1]:
                                clusters[-1].append(nh)
                        return clusters

            if root in leaves: #this was in an else before but is still apparently necessary?
                    leaves.remove(root)
                
            #if layer %10==0:
                ##print("Layer",layer)
                
            

            
        for leaf in leaves:
            if layer>1 and abs(pops[leaf][1]-pop_target) < pop_target * epsilon:
                ##print(pops[leaf][1]/pop_target)
                #ST.remove_edge(leaf,pred[leaf])#One option but slow
                #parts=list(nx.connected_components(h)) #ST here too
                ##print(layer, len(parts))

                #part=parts[random.random()<.5]
                clusters={}
                clusters[1]=list(pops[leaf][0])
                clusters[-1]=[]
                for nh in graph.nodes():
                    if nh not in clusters[1]:
                        clusters[-1].append(nh)
                return clusters

            parent = pred[leaf]
            
            pops[parent][1]+=pops[leaf][1]
            pops[parent][0]=pops[parent][0].union(pops[leaf][0])
            #h = nx.contracted_edge(h,(parent,leaf),self_loops = False)#too slow on big graphs
            h.remove_node(leaf)
            leaves.remove(leaf)
            t=t+1
            #if t%1000==0:
            #    #print(t)
         
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
