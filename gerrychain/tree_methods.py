import random
import networkx as nx
import geopandas as gp
from networkx.algorithms import tree
import itertools
from functools import partial

def recursive_tree_part(partition,graph, parts, pop_col, epsilon,node_repeats=20,):
    newlabels={}
    pop_target=0
    for node in graph.nodes():
        pop_target+=partition.graph.node_attribute(pop_col)[node]
    pop_target=pop_target/parts
    
    remaining_nodes=list(graph.nodes())
    for n in newlabels.keys():
        remaining_nodes.remove(n)
		
    sgraph=nx.subgraph(graph,remaining_nodes)
    
    for i in range(parts-1):
        update=tree_part2(partition, sgraph, pop_col, pop_target, epsilon,node_repeats)#should be part2
        print("updated")
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
	
	
	
def tree_part2(partition, graph, pop_col, pop_target, epsilon,node_repeats):
    
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
    #print(root)
    predbfs=nx.bfs_predecessors(h, root)#was dfs
    pred={}
    for ed in predbfs:
        pred[ed[0]]=ed[1]

    pops={x:[{x},partition.graph.node_attribute(pop_col)[x]] for x in graph.nodes()}
    
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
            #print(root)
            predbfs=nx.bfs_predecessors(h, root)#was dfs
            pred={}
            for ed in predbfs:
                pred[ed[0]]=ed[1]

            pops={x:[{x},partition.graph.node_attribute(pop_col)[x]] for x in graph.nodes()}
    
            leaves=[]
            t=0
            layer=0
            restarts=0
            #print("Bad tree -- rebuilding")
            
        if len(list(h.nodes()))==1:
            h=ST.copy()
            root = random.choice([x for x in ST.nodes() if ST.degree(x)>1])#this used to be greater than 2 but failed on small grids:(
            #print(root)
            #pred=nx.bfs_predecessors(h, root)#was dfs
            predbfs=nx.bfs_predecessors(h, root)#was dfs
            pred={}
            for ed in predbfs:
                pred[ed[0]]=ed[1]
            pops={x:[{x},partition.graph.node_attribute(pop_col)[x]] for x in graph.nodes()}
            #print("bad root --- restarting",restarts)
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
                        print(1,pops[leaf][1]/pop_target)
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
                #print("Layer",layer)
                
            

            
        for leaf in leaves:
            if layer>1 and abs(pops[leaf][1]-pop_target) < pop_target * epsilon:
                #print(pops[leaf][1]/pop_target)
                #ST.remove_edge(leaf,pred[leaf])#One option but slow
                #parts=list(nx.connected_components(h)) #ST here too
                #print(layer, len(parts))

                #part=parts[random.random()<.5]
                print(2,pops[leaf][1]/pop_target)#added this new but seems to be the working one
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
            #    print(t)

##### Spanning Tree Generation
			

def get_spanning_tree_u_ab(graph):
    w=graph.copy()

    node_set=set(w.nodes())
    x0=random.choice(tuple(node_set))

    node_set.remove(x0)

    current=x0
    tedges=[]

    while node_set != set():
        next=random.choice(list(w.neighbors(current)))
        if next in node_set:
            node_set.remove(next)
            tedges.append((current, next))
        current=next


    return tedges


def get_spanning_tree_u_w(graph):
    w=graph.copy()
    node_set=set(w.nodes())
    x0=random.choice(tuple(node_set))
    x1=x0
    while x1==x0:
        x1=random.choice(tuple(node_set))
    node_set.remove(x1)
    tnodes ={x1}
    tedges=[]
    current=x0
    current_path=[x0]
    #print(x0,x1)
    current_edges=[]
    while node_set != set():
        #print("path started")
        next=random.choice(list(w.neighbors(current)))
        current_edges.append((current,next))
        current = next
        current_path.append(next)

        if next in tnodes:
            #print(current_path,current_edges)
            for x in current_path[:-1]:
                node_set.remove(x)
                tnodes.add(x)
            for ed in current_edges:
                tedges.append(ed)
            current_edges = []
            if node_set != set():
                current=random.choice(tuple(node_set))
            current_path=[current]


        if next in current_path[:-1]:
            #print("cp:",current_path,"ce:",current_edges)
            current_path.pop()
            current_edges.pop()
            for i in range(len(current_path)):
                if current_edges !=[]:
                    current_edges.pop()
                if current_path.pop() == next:
                    break
            #print("cp:",current_path,"ce:",current_edges)
            if len(current_path)>0:
                current=current_path[-1]
            else:
                current=random.choice(tuple(node_set))
                current_path=[current]




    return tedges





def get_spanning_tree_k(graph):
    w=graph.copy()
    for ed in w.edges():
        w.add_edge(ed[0],ed[1],weight=random.random())

    T = tree.maximum_spanning_edges(w, algorithm='kruskal', data=False)
    return T
			
			
##### Helper functions for Ents


def tree_cycle_walk_all(partition, tree):

    tempo=0
    tedges=set(tree.edges())
    while tempo==0:

        edge = random.choice(tuple(partition.graph.edges()))
        if (edge[0],edge[1]) not in tedges and (edge[1],edge[0]) not in tedges:
            tempo=1
            tree.add_edge(edge[0],edge[1])
            ncycle=nx.find_cycle(tree,edge[0])
            print("length of tree cycle:", len(ncycle))
            cutedge=random.choice(tuple(ncycle))
            tree.remove_edge(cutedge[0],cutedge[1])
            return tree


def tree_cycle_walk_cut(partition, tree):


    tempo=0
    tedges=set(tree.edges())
    while tempo==0:
        edge = random.choice(tuple(partition["cut_edges"]))
        #print("picked an edge")
        if (edge[0],edge[1]) not in tedges and (edge[1],edge[0]) not in tedges:
            tempo=1
            tree.add_edge(edge[0],edge[1])
            ncycle=nx.find_cycle(tree,edge[0])
            print("length of tree cycle:", len(ncycle))
            cutedge=random.choice(tuple(ncycle))
            tree.remove_edge(cutedge[0],cutedge[1])
            return tree



def partition_spanning_tree_single(partition):

    graph=partition.graph

    tgraph=nx.Graph()
    sgn={}
    for label in partition.parts:
        #print(label)
        sgn[label]=[]#make this a dictionary
    for n in graph.nodes():

        sgn[partition.assignment[n]].append(n)
    for label in partition.parts:
        sgraph = nx.subgraph(graph, sgn[label])
        tempT = get_spanning_tree_u_w(sgraph)#get_spanning_tree_k(sgraph)
        tgraph.add_edges_from(tempT)

        #print("done with inividual") #pretty fast anyway





    el=set()
    for edge in partition["cut_edges"]:
        el.add((partition.assignment[edge[0]],partition.assignment[edge[1]]))
    #print("set f edges")
    w=nx.Graph()
    w.add_edges_from(list(el))
    #print("built district graph")
    for ed in w.edges():
        w.add_edge(ed[0],ed[1],weight=random.random())

    T = tree.maximum_spanning_edges(w, algorithm='kruskal', data=False)
    ST= nx.Graph()
    ST.add_edges_from(list(T))
    #print("built district tree")


    e_to_add=[]

    for edge in ST.edges():
        tempo=0
        templ=tuple(partition["cut_edges_by_part"][edge[0]])
        #print(edge[0],edge[1])
        #rint("new district edge")
        while tempo==0:
            qedge = random.choice(templ)
            #print("tried an edge",[partition.assignment[qedge[0]],partition.assignment[qedge[1]]])
            if edge[1] == partition.assignment[qedge[0]] or edge[1] == partition.assignment[qedge[1]]:
                tempo = 1
                e_to_add.append(qedge)



    tgraph.add_edges_from(e_to_add)

    return tgraph



def partition_spanning_tree_all(partition):
    graph=partition.graph

    tgraph=nx.Graph()

    for label in partition.parts:
        sgn=[]
        for n in graph.nodes():
            if partition.assignment[n] ==label:#[2,3]: #[1,3]
                sgn.append(n)
        sgraph = nx.subgraph(graph,sgn)
        tempT= get_spanning_tree_k(sgraph)
        tgraph.add_edges_from(tempT)




    tgraph.add_edges_from(list(partition["cut_edges"]))

    t2graph=nx.Graph()
    t2graph.add_edges_from(get_spanning_tree_k(tgraph))


    return t2graph




##### Tree Splitting

def tree_cut_delta(partition,ST, pop_col, pop_target, epsilon, node_repeats=5):



    graph=partition.graph
    h=ST.copy()

    #nx.draw(ST,layout='tree')

    #root = random.choice(list(h.nodes()))
    root = random.choice([x for x in ST.nodes() if ST.degree(x)>2]) # probably should be 2 maybe doesn't matter?
    #print(root)
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

            return {}

        if len(list(h.nodes()))==1:
            h=ST.copy()
            root = random.choice([x for x in ST.nodes() if ST.degree(x)>2])
            #print(root)
            #pred=nx.bfs_predecessors(h, root)#was dfs
            predbfs=nx.bfs_predecessors(h, root)#was dfs
            pred={}
            for ed in predbfs:
                pred[ed[0]]=ed[1]
            pops={x:[{x},graph.nodes[x][pop_col]] for x in graph.nodes()}
            #print("bad root --- restarting",restarts)
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
                        print(pops[leaf][1]/pop_target)
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
                #print("Layer",layer)




        for leaf in leaves:
            if layer>1 and abs(pops[leaf][1]-pop_target) < pop_target * epsilon:
                #print(pops[leaf][1]/pop_target)
                #ST.remove_edge(leaf,pred[leaf])#One option but slow
                #parts=list(nx.connected_components(h)) #ST here too
                #print(layer, len(parts))

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
            #    print(t)

def recursive_tree_full(partition,ST, parts, pop_col, epsilon, node_repeats=5):
    graph=partition.graph
    newlabels={}
    pop_target=0
    for node in graph.nodes():
        pop_target+=graph.node_attribute(pop_col)[node]
    pop_target=pop_target/parts

    #remaining_nodes=list(graph.nodes())
    #for n in newlabels.keys():
    #    remaining_nodes.remove(n)
    #sgraph=nx.subgraph(ST, remaining_nodes)
    #print("built subgraph")
    remaining_nodes=list(graph.nodes())
    sgraph=ST
    for i in range(parts-1):
        update=tree_cut_delta(partition, sgraph, pop_col, pop_target, epsilon, node_repeats)
        #print("built part", i)
        if update == {}:
            print("gave up on this tree")
            return {}

        else:
            for x in list(update[1]):
                newlabels[x]=i
                remaining_nodes.remove(x)
        #update pop_target?
        #remaining_nodes=list(graph.nodes())
        #for n in newlabels.keys():
            #remaining_nodes.remove(n) #Moved these three lines up above into the x for loop does it work?

        sgraph=nx.subgraph(ST,remaining_nodes)
        #print("Built  #", i)

    td=set(newlabels.keys())
    for nh in graph.nodes():
        if nh not in td:
            newlabels[nh]=parts-1#was parts+1

    print("finished whole tree")
    return newlabels




##### Mixed proposals 

def tree_mixed_proposal(partition):

    if random.random() <.05:
        flips=propose_bounce_single_cut(partition)
    else:
        flips = propose_random_flip(partition)

    return flips

def merge_mixed_proposal(partition):

    if random.random() <.05:
        flips=propose_merge2_tree(partition)
    else:
        flips = propose_random_flip(partition)

    return flips
			
			
			
			
##### (Uniform?) Full-Tree Methods


def propose_allk_tree(partition):
    tree=nx.Graph()
    tree.add_edges_from(list(get_spanning_tree_k(partition.graph)))

    clusters = recursive_tree_full(partition,tree,len(partition.parts),"POP10",.02,5)

    return clusters
	
	
def propose_allk_tree(partition):
    tree=nx.Graph()
    tree.add_edges_from(list(get_spanning_tree_u_w(partition.graph)))

    clusters = recursive_tree_full(partition,tree,len(partition.parts),"POP10",.02,5)

    return clusters
	
	
	

			
			
##### These are different experiments for the ent walk

def propose_bounce_single_all(partition):

    tree = partition_spanning_tree_single(partition)

    tree = tree_cycle_walk_all(partition, tree)

    clusters = recursive_tree_full(partition,tree,len(partition.parts),"population",.02,5)

    return clusters

def propose_bounce_single_cut(partition):
    tree = partition_spanning_tree_single(partition)

    tree = tree_cycle_walk_cut(partition, tree)

    clusters = recursive_tree_full(partition,tree,len(partition.parts),"population",.05,2)

    return clusters

def propose_bounce_allcut_all(partition):
    tree = partition_spanning_tree_all(partition)

    tree = tree_cycle_walk_all(partition, tree)

    clusters = recursive_tree_full(partition,tree,len(partition.parts),"POP10",.2,10)

    return clusters

def propose_bounce_allcut_cut(partition):

    tree = partition_spanning_tree_all(partition)

    tree = tree_cycle_walk_cut(partition, tree)

    clusters = recursive_tree_full(partition,tree,len(partition.parts),"population",.2,10)

    return clusters

	
	
	
##### Merge Proposal


def propose_merge2_tree(partition):
    edge = random.choice(tuple(partition['cut_edges']))
    #print(edge)
    et=[partition.assignment[edge[0]],partition.assignment[edge[1]]]
    #print(et)
    sgn=[]
    for n in partition.graph.nodes():
        if partition.assignment[n] in et:
            sgn.append(n)

    #print(len(sgn))
    sgraph = nx.subgraph(partition.graph,sgn)

    edd={0:et[0],1:et[1]}

    #print(edd)

    clusters = recursive_tree_part(partition,sgraph,2,"POP10",.05,10)
    print("finished rtp")
    #print(len(clusters))
    flips={}
    for val in clusters.keys():
        flips[val]=edd[clusters[val]]

    #print(len(flips))
    #print(partition.assignment)
    #print(flips)
    return flips
	
	
##### Partial Func

def propose_merge2_tree_partial(partition,pop_col,epsilon,node_repeats):
    edge = random.choice(tuple(partition['cut_edges']))
    #print(edge)
    et=[partition.assignment[edge[0]],partition.assignment[edge[1]]]
    #print(et)
    sgn=[]
    for n in partition.graph.nodes():
        if partition.assignment[n] in et:
            sgn.append(n)

    #print(len(sgn))
    sgraph = nx.subgraph(partition.graph,sgn)

    edd={0:et[0],1:et[1]}

    #print(edd)

    clusters = recursive_tree_part(partition,sgraph,2,pop_col=pop_col,epsilon=epsilon,node_repeats=node_repeats)
    print("finished rtp")
    #print(len(clusters))
    flips={}
    for val in clusters.keys():
        flips[val]=edd[clusters[val]]

    #print(len(flips))
    #print(partition.assignment)
    #print(flips)
    return flips
	

#merge_prop = partial(propose_merge2_tree_partial,pop_col="POP10",epsilon=.05,node_repeats=10)