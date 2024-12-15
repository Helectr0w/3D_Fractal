from panda3d.core import GeomVertexFormat, GeomVertexData, Geom, GeomNode, GeomTriangles, GeomVertexWriter
from panda3d.core import NodePath
from panda3d.core import AmbientLight, DirectionalLight, ColorAttrib
from direct.showbase.ShowBase import ShowBase
import numpy as np
import random


# Fonction pour générer un terrain fractal (Diamond-Square)
def diamond_square(size, roughness):
    grid_size = 2 ** size + 1
    grid = np.zeros((grid_size, grid_size))
    
    grid[0, 0] = random.uniform(-1, 1)
    grid[0, -1] = random.uniform(-1, 1)
    grid[-1, 0] = random.uniform(-1, 1)
    grid[-1, -1] = random.uniform(-1, 1)

    def diamond_step(x, y, step_size, scale):
        avg = (
            grid[x - step_size, y - step_size]
            + grid[x - step_size, y + step_size]
            + grid[x + step_size, y - step_size]
            + grid[x + step_size, y + step_size]
        ) / 4.0
        grid[x, y] = avg + random.uniform(-scale, scale)

    def square_step(x, y, step_size, scale):
        points = []
        if x - step_size >= 0: points.append(grid[x - step_size, y])
        if x + step_size < grid_size: points.append(grid[x + step_size, y])
        if y - step_size >= 0: points.append(grid[x, y - step_size])
        if y + step_size < grid_size: points.append(grid[x, y + step_size])
        
        avg = sum(points) / len(points)
        grid[x, y] = avg + random.uniform(-scale, scale)

    step_size = grid_size - 1
    scale = roughness

    while step_size > 1:
        half_step = step_size // 2
        for x in range(half_step, grid_size - 1, step_size):
            for y in range(half_step, grid_size - 1, step_size):
                diamond_step(x, y, half_step, scale)
        
        for x in range(0, grid_size, half_step):
            for y in range((x + half_step) % step_size, grid_size, step_size):
                square_step(x, y, half_step, scale)

        step_size //= 2
        scale /= 2

    return grid


# Classe principale avec contrôles et couleurs
class FractalTerrainApp(ShowBase):
    def __init__(self):
        super().__init__()
        self.disableMouse()  # Désactiver le contrôle caméra par défaut

        # Générer le terrain
        size = 7
        roughness = 1.0
        terrain = diamond_square(size, roughness)
        terrain -= terrain.min()
        terrain /= terrain.max()

        # Créer un modèle 3D pour le terrain
        terrain_node = self.generate_terrain_model(terrain, scale=10)
        terrain_node.reparentTo(self.render)

        # Ajouter des lumières
        self.add_lighting()

        # Variables pour caméra d'orbite
        self.orbit_center = terrain_node.getBounds().getCenter()
        self.camera_distance = 50
        self.camera_angle_h = 45
        self.camera_angle_v = -30
        self.zoom_speed = 2.0

        # Configurer la caméra initialement
        self.update_camera()

        # Activer les événements pour la caméra
        self.accept("wheel_up", self.zoom_camera, [-1])
        self.accept("wheel_down", self.zoom_camera, [1])
        self.taskMgr.add(self.camera_control_task, "camera_control_task")

    def generate_terrain_model(self, terrain, scale):
        rows, cols = terrain.shape
        vertex_format = GeomVertexFormat.getV3cp()
        vertex_data = GeomVertexData("terrain", vertex_format, Geom.UHDynamic)
        vertex_writer = GeomVertexWriter(vertex_data, "vertex")
        color_writer = GeomVertexWriter(vertex_data, "color")

        for i in range(rows):
            for j in range(cols):
                x, y, z = i * scale / (rows - 1), j * scale / (cols - 1), terrain[i, j] * scale
                vertex_writer.addData3(x - scale / 2, y - scale / 2, z)
                
                # Définir la couleur en fonction de l'altitude
                if z < 2:
                    color = (0.2, 0.4, 1.0, 1)  # Bleu (eau)
                elif z < 4:
                    color = (0.0, 0.6, 0.2, 1)  # Vert (herbe)
                elif z < 6:
                    color = (0.5, 0.4, 0.2, 1)  # Marron (roche)
                else:
                    color = (1.0, 1.0, 1.0, 1)  # Blanc (neige)
                color_writer.addData4(*color)

        geom = Geom(vertex_data)
        triangles = GeomTriangles(Geom.UHStatic)
        for i in range(rows - 1):
            for j in range(cols - 1):
                v0 = i * cols + j
                v1 = v0 + 1
                v2 = v0 + cols
                v3 = v2 + 1

                triangles.addVertices(v0, v2, v1)
                triangles.addVertices(v1, v2, v3)

        geom.addPrimitive(triangles)
        terrain_node = GeomNode("terrain")
        terrain_node.addGeom(geom)
        return NodePath(terrain_node)

    def add_lighting(self):
        ambient_light = AmbientLight("ambient")
        ambient_light.setColor((0.5, 0.5, 0.5, 1))
        ambient_node = self.render.attachNewNode(ambient_light)
        self.render.setLight(ambient_node)

        directional_light = DirectionalLight("directional")
        directional_light.setColor((1, 1, 1, 1))
        directional_node = self.render.attachNewNode(directional_light)
        directional_node.setHpr(0, -45, 0)
        self.render.setLight(directional_node)

    def update_camera(self):
        x = self.orbit_center.getX() + self.camera_distance * np.cos(np.radians(self.camera_angle_h)) * np.cos(np.radians(self.camera_angle_v))
        y = self.orbit_center.getY() + self.camera_distance * np.sin(np.radians(self.camera_angle_h)) * np.cos(np.radians(self.camera_angle_v))
        z = self.orbit_center.getZ() + self.camera_distance * np.sin(np.radians(self.camera_angle_v))
        self.camera.setPos(x, y, z)
        self.camera.lookAt(self.orbit_center)

    def zoom_camera(self, direction):
        self.camera_distance = max(10, self.camera_distance + direction * self.zoom_speed)
        self.update_camera()

    def camera_control_task(self, task):
        if self.mouseWatcherNode.is_button_down("mouse3"):
            md = self.win.getPointer(0)
            x, y = md.getX(), md.getY()
            dx, dy = x - self.win.getXSize() // 2, y - self.win.getYSize() // 2

            self.camera_angle_h -= dx * 0.2
            self.camera_angle_v = max(-80, min(80, self.camera_angle_v - dy * 0.2))

            self.win.movePointer(0, self.win.getXSize() // 2, self.win.getYSize() // 2)
            self.update_camera()

        return task.cont


app = FractalTerrainApp()
app.run()
