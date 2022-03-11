from dataclasses import dataclass
import numpy as np
import pandas as pd
import os
import re

import forsys.vertex as vertex
import forsys.edge as edge
import forsys.cell as cell

@dataclass
class SurfaceEvolver:
    fname: str

    # def __post_init__(self):
    #   pass

    def create_lattice(self):
        # create all vertex elements
        edges_temp = self.get_edges()
        
        vertices = {}
        for _, r in self.get_vertices().iterrows():          
            vertices[int(r.id)] = vertex.Vertex(int(r.id), r.x, r.y)
            
        edges  = {}
        for _, r in edges_temp.iterrows():
            edges[int(r.id)] = edge.Edge(int(r.id), vertices[int(r.id1)], vertices[int(r.id2)])
            edges[int(r.id)].gt = round(edges_temp.loc[edges_temp['id'] == int(r.id)]['force'].iloc[0], 4)

        cells = {}
        for _, r in self.get_cells().iterrows():
            vlist = [edges[abs(e)].v1 if e > 0 else edges[abs(e)].v2 for e in r.edges]
            cells[int(r.id)] = cell.Cell(int(r.id), vlist, {})

        # delete all vertices and edges with no cell
        vertex_to_delete = []
        # edge_to_delete = []
        for vid, v in vertices.items():
            if len(v.ownCells) == 0:
                vertex_to_delete.append(int(vid))
        for i in vertex_to_delete:
            for e in vertices[i].ownEdges.copy():
                try:
                    del edges[e] 
                except KeyError:
                    pass
        
            del vertices[i]

        return vertices, edges, cells

    def calculate_first_last(self):
        with open(os.path.join(self.fname),"r") as f:
            ini_v = next(index for index, line in enumerate(f) if line.startswith("vertices  "))
            fin_v = next(index for index, line in enumerate(f) if line.startswith("edges  ")) + ini_v
            f.seek(0)
            ini_e = next(index for index, line in enumerate(f) if line.startswith("edges  "))
            fin_e = next(index for index, line in enumerate(f) if line.startswith("faces  ")) + ini_e
            f.seek(0)
            ini_f = next(index for index, line in enumerate(f) if line.startswith("faces  "))
            fin_f = next(index for index, line in enumerate(f) if line.startswith("bodies  ")) + ini_f

        self.index_v = (ini_v, fin_v)
        self.index_e = (ini_e, fin_e)
        self.index_f = (ini_f, fin_f)

        return self.index_v, self.index_e, self.index_f


    def get_first_last(self):
        try:
            return self.index_v, self.index_e, self.index_f
        except AttributeError:
            return self.calculate_first_last()
    
    def get_vertices(self):
        vertices = pd.DataFrame()
        ids = []
        xs = []
        ys = []

        index_v, _, _ = self.get_first_last()

        with open(os.path.join(self.fname), "r") as f:
            lines = f.readlines()
            for i in range(index_v[0] + 1, index_v[1]):
                ids.append(int(re.search(r"\d+", lines[i]).group()))
                xs.append(round(float(lines[i].split()[1]), 3))
                ys.append(round(float(lines[i].split()[2]), 3))
                # vals.append(float(lines[i][lines[i].find("density"):].split(" ")[1]))
        vertices['id'] = ids
        vertices['x'] = xs
        vertices['y'] = ys

        return vertices
    
    def get_edges(self):
        edges = pd.DataFrame()
        ids = []
        id1 = []
        id2 = []
        forces = []

        _, index_e, _ = self.get_first_last()

        with open(os.path.join(self.fname), "r") as f:
            lines = f.readlines()
            for i in range(index_e[0] + 1, index_e[1]):
                ids.append(int(re.search(r"\d+", lines[i]).group()))
                id1.append(int(lines[i].split()[1]))
                id2.append(int(lines[i].split()[2]))
                forces.append(float(lines[i].split()[4]) if lines[i].split()[3] == "density" else 1)
                # vals.append(float(lines[i][lines[i].find("density"):].split(" ")[1]))
        edges['id'] = ids
        edges['id1'] = id1
        edges['id2'] = id2
        edges['force'] = forces
        return edges

    def get_cells(self):
        cells = pd.DataFrame()
        ids = []
        edges = []

        _, _, index_f = self.get_first_last()

        with open(os.path.join(self.fname), "r") as f:
            lines = f.readlines()
            current_edge = []
            first = True

            for i in range(index_f[0] + 1, index_f[1]):
                splitted = lines[i].split()
                if first and "*/" not in splitted[-1]:
                    ids.append(splitted[0])
                    first = False
                    current_edge = current_edge+splitted[1:-1]
                elif splitted[-1] == '\\' and not first:
                    current_edge = current_edge+splitted[0:-1]
                elif "*/" in splitted[-1]:
                    # last line, save
                    if first:
                        ids.append(splitted[0])
                        current_edge = current_edge+splitted[1:-2]
                    else:
                        current_edge = current_edge+splitted[0:-2]
                    edges.append([int(e) for e in current_edge])
                    current_edge = []
                    first = True
        
        cells['id'] = ids
        cells['edges'] = edges

        return cells
