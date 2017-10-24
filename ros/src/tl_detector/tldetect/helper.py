from collections import namedtuple
from math import sqrt
import random
import numpy as np
try:
    import Image
except ImportError:
    from PIL import Image

Point = namedtuple('Point', ('coords', 'n', 'ct'))
Cluster = namedtuple('Cluster', ('points', 'center', 'n'))

def get_points(img):
    points = []
    w, h = img.size
    for count, color in img.getcolors(w * h):
        points.append(Point(color, 3, count))
    return points

rtoh = lambda rgb: '#%s' % ''.join(('%02x' % p for p in rgb))

def colorz(img, n=3):
#     img = Image.open(filename)
    img.thumbnail((200, 200))
    w, h = img.size

    points = get_points(img)
    clusters = kmeans(points, n, 1)
    rgbs = [map(int, c.center.coords) for c in clusters]
    from scipy import spatial
#     start = time.time()
    red = [241, 45, 45]
    red = np.array(red)
    green = [78, 209, 119]
    green = np.array(green)
    yellow = [198, 209, 110]
    yellow = np.array(yellow)
    thres = 0.99
    for color in list(rgbs):
        color_val = np.array(list(color))
        dist_to_red = 1 - spatial.distance.cosine(red,color_val)
        dist_to_green = 1 - spatial.distance.cosine(green,color_val)
        dist_to_yellow = 1 - spatial.distance.cosine(yellow,color_val)
        if(dist_to_red>thres):
            return "RED"
        if(dist_to_green>thres):
            return "GREEN"
        if(dist_to_yellow>thres):
            return "YELLOW"
    return "UNK"

def euclidean(p1, p2):
    return sqrt(sum([
        (p1.coords[i] - p2.coords[i]) ** 2 for i in range(p1.n)
    ]))

def calculate_center(points, n):
    vals = [0.0 for i in range(n)]
    plen = 0
    for p in points:
        plen += p.ct
        for i in range(n):
            vals[i] += (p.coords[i] * p.ct)
    return Point([(v / plen) for v in vals], n, 1)

def kmeans(points, k, min_diff):
    clusters = [Cluster([p], p, p.n) for p in random.sample(points, k)]

    while 1:
        plists = [[] for i in range(k)]

        for p in points:
            smallest_distance = float('Inf')
            for i in range(k):
                distance = euclidean(p, clusters[i].center)
                if distance < smallest_distance:
                    smallest_distance = distance
                    idx = i
            plists[idx].append(p)

        diff = 0
        for i in range(k):
            old = clusters[i]
            center = calculate_center(plists[i], old.n)
            new = Cluster(plists[i], center, old.n)
            clusters[i] = new
            diff = max(diff, euclidean(old.center, new.center))

        if diff < min_diff:
            break

    return clusters