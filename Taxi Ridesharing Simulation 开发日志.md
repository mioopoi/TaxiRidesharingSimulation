# Taxi Ridesharing Simulation 开发文档

作者：李华繁

整理时间：2017.03.03

---

`2016.12.08`

打算采用[GeoHash](https://en.wikipedia.org/wiki/Geohash)对北京市的地理信息进行建模。所以还是需要静态的路网数据（虽然轨迹数据也行，但是其冗余度可能比较大，计算时会影响复杂度，需要做预处理）。运气不错的是，在 http://www.datatang.com/data/45422 找到了北京路网数据。

`2016.12.09-2016.12.13`

## 数据和预处理

这份北京市路网数据，有`171504`个节点路口（节点），`433391`条路段（边）。每个节点有3个字段：

| 字段     | 含义   |
| ------ | ---- |
| `v_id` | 节点id |
| `lat`  | 纬度   |
| `lon`  | 经度   |

每条边有3个字段：

| 字段          | 含义      |
| ----------- | ------- |
| `e_id`      | 边id     |
| `start_vid` | 开始节点的id |
| `end_vid`   | 结束节点的id |

经过验证，节点id和边id都是连续编号的整数；图是有向图，从节点和边的数量关系来看，是比较稀疏的图；不一定所有节点都连通。所以如果连通性很弱的话，对于图的计算可能会带来一定的困难。

其实还有一个数据文件，里面存放了每条边上的点采样（因为一条路段不总是笔直的），这里暂时不使用这个，等主程序写完了，要完善的话再用上。（不使用这份数据带来的主要问题在于会对出租车动态位置的计算造成一定的误差。另外就是，如果换个城市，就不一定有这个数据了）

数据文件是`.txt`格式的，先用MATLAB做个预处理，算出每条边的路程长度，并把文件转换成`.csv`格式（便于Python更方便地导入）。

- 注意地理上两点之间的距离不能简单地采用欧式距离计算，而应该采用球面距离公式。


- MATLAB中，可以调用`distance`函数计算球面两点距离：设两点的经纬度分别是lat1, lat2, lon1, lon2，计算方法如下:

```matlab
d = distance(lat1, lon1, lat2, lon2)  % (lat1, lon1), (lat2, lon2)分别是两个点的坐标(纬度, 经度)
length = d * 6371 * 1000 * 2 * pi / 360  % 单位是m，其中6371(km)是地球平均半径
```

计算完发现有异常数据：极少数（个别）的边长度很长，比如`e_id`为`425125`的边，长度达到了70多公里，这是不太可能的，经检查发现是其起点有问题。不过由于这样的边很少（不超过10条），暂时也不做处理了。

## 整体模块设计

主编程语言选用Python。模块划分如下：

![modules](https://cl.ly/2n2f2f1w0m3x/Image%202016-12-11%20at%2010.01.28%20PM.png)

- `simulation.py` 仿真系统的主程序
- `location.py` 对地理信息的抽象、相关的地理计算utilities（如距离）
- `road_network.py` 对底层道路网络的抽象、相关的图计算utilities（如最短路径）
- `geohash.py` 对地理信息的GeoHash编、解码
- `spatio_temporal_index.py` 时空数据库，基于GeoHash建立上层时空索引（网格化）
- `query.py` 对乘客请求的抽象
- `taxi.py` 对司机(taxi)的抽象
- `dispatcher.py` 派车策略服务提供模块 (taxi searching)
- `route.py` 路径规划服务提供模块 (taxi scheduling)


## location.py

定义抽象类型`Location`。

```python
"""
Description: This module contains the abstraction for the geographical location on the earth.
Author: Huafan Li
Date: 2016/12/09
"""


from geohash import geo_encode
import math


class Location:
    def __init__(self, lat, lon):
        """
        Initialize a location.

        The Location class is the abstraction of a geographical position on the earth.

        :param lat: float
            latitude of a location
        :param lon: float
            longitude of a location
        :return: None
        """
        self.lat = lat
        self.lon = lon
        self.geohash = geo_encode(lat, lon, 6)

    def __str__(self):
        """
        Return a string representation.

        :return: str

        >>> location = Location(39.564540, 115.739662)
        >>> print(location)
        (39.56454, 115.739662)
        >>> print(location.geohash)
        wx431d
        """
        return "({}, {})".format(self.lat, self.lon)

    def __eq__(self, other):
        """
        Return True if self equals other, and false otherwise.

        :param other: Location
        :return: bool

        >>> pos_a = Location(39.564540, 115.739662)
        >>> pos_b = Location(39.564540, 115.739662)
        >>> pos_a == pos_b
        True
        """
        return self.lat == other.lat and self.lon == other.lon


def get_distance(pos_a, pos_b):
    """
    Compute the distance between two location in meters.

    :param pos_a: Location
    :param pos_b: Location
    :return: float

    >>> pos_a = Location(39.564540, 115.739662)
    >>> pos_b = Location(39.564540, 115.739662)
    >>> pos_c = Location(39.533867, 115.746735)
    >>> print(get_distance(pos_a, pos_b))
    0.0
    >>> print(get_distance(pos_a, pos_c))
    3464.17661119
    """
    r = 6371 * 10**3  # radius of the earth
    x1 = math.radians(pos_a.lat)
    y1 = math.radians(pos_a.lon)
    x2 = math.radians(pos_b.lat)
    y2 = math.radians(pos_b.lon)
    temp = math.cos(x1) * math.cos(x2) * math.cos(y1 - y2) + math.sin(x1) * math.sin(x2)
    if temp > 1.000:
        temp = 1.0
    elif temp < -1.000:
        temp = -1.0
    dis = r * math.acos(temp)
    return dis
```

## geohash.py

提供GeoHash的编码和解码函数。关于GeoHash的解释参见[Wikipedia](https://en.wikipedia.org/wiki/Geohash)，实现上采用二分搜索。

```python
"""
Description: This module contains the utilities for the encoding and decoding of GeoHash.
Author: Huafan Li
Date: 2016/12/09

=== Constants ===
BASE32: list
    A list used for base32 encoding and decoding of GeoHash
"""

BASE32 = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'b', 'c', 'd', 'e', 'f', 'g',
          'h', 'j', 'k', 'm', 'n', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']


def geo_encode(lat, lon, precision):
    global BASE32

    lat_interval = [-90.0, 90.0]
    lon_interval = [-180.0, 180.0]
    length = precision * 5  # the demand length of binary code
    geohash = ""
    bits = 0
    for i in range(1, length + 1):
        if not(i % 2 == 0):  # odd: lon
            mid = (lon_interval[0] + lon_interval[1]) / 2
            if lon > mid:
                bits = bits * 2 + 1  # binary code is set to 1
                lon_interval[0] = mid  # update the corresponding interval
            else:
                bits *= 2  # binary code is set to 0
                lon_interval[1] = mid
        else:
            mid = (lat_interval[0] + lat_interval[1]) / 2
            if lat > mid:
                bits = bits * 2 + 1
                lat_interval[0] = mid
            else:
                bits *= 2
                lat_interval[1] = mid
        if i % 5 == 0:
            geohash += BASE32[bits]
            bits = 0  # reset binary code
    return geohash


def geo_decode(geohash):
    global BASE32

    odd = True
    lat_interval = [-90.0, 90.0]
    lon_interval = [-180.0, 180.0]
    for char in geohash:
        bits = BASE32.index(char)
        for j in range(4, -1, -1):
            bit = (bits >> j) & 1
            if odd:
                mid = (lon_interval[0] + lon_interval[1]) / 2
                lon_interval[1-bit] = mid
            else:
                mid = (lat_interval[0] + lat_interval[1]) / 2
                lat_interval[1-bit] = mid
            odd = not odd
    lat = (lat_interval[0] + lat_interval[1]) / 2
    lon = (lon_interval[0] + lon_interval[1]) / 2
    return [lat, lon]
```

## road_network.py

定义节点类`Vertex`, 边类`Edge`, 以及整个路网的抽象数据类型`RoadNetwork`。该文件的代码量比较大，就不贴在这里了。

存储图的数据结构：邻接表（17万个节点，用邻接矩阵太费空间）。

文件读取：调用`Pandas`的`read_csv()`

本来还有点担心内存，建好图后，测试了一下，发现是多虑了。读取所有的节点和边，大概30s，内存只占用了6% (内存容量为8 GB)。

相关计算：

新建了一个模块：`container.py`，以提供计算所需的数据结构（队列和优先队列），代码如下：

```python
import collections
import heapq


class Queue:
    def __init__(self):
        self.elements = collections.deque()

    def empty(self):
        return len(self.elements) == 0

    def put(self, x):
        self.elements.append(x)

    def get(self):
        return self.elements.popleft()


class PriorityQueue:
    def __init__(self):
        self.elements = []

    def empty(self):
        return len(self.elements) == 0

    def put(self, item, priority):
        heapq.heappush(self.elements, (priority, item))

    def get(self):
        return heapq.heappop(self.elements)[1]
```

- 两点之间可达性：Breadth First Search (with early exit)

即便是Breadth First Search，随便选了几个节点，都能在0.5s内判断它们是否连通。这份数据还是可以的，节点之间的连通性挺好。

- 两点之间最短路径：Breadth First Search, Dijkstra's Algorithm, Greedy Best First Search, [A-star Algorithm](https://en.wikipedia.org/wiki/A*_search_algorithm)

前两个算法基本都可以认为是比较暴力的盲目搜索，后两种算法都是启发式算法。Greedy-BFS在图搜索中被人提及得比较少，但它的效率往往非常高的，因为它探寻的空间很小，其原理就是遵循一个启发式策略，沿着状态空间的某一个方向搜索，它没有Dijkstra's Algorithm中的“松弛”操作，所以不能保证解的质量。A-star Algorithm综合了Dijkstra's Algorithm和Greedy-BFS的优点。对于仅仅求两个点之间的最短路径，最好的算法自然是A-star，Dijkstra's Algorithm实际上是求了从起点到图中所有点的最短路径，多了很多不必要的计算。A-star的关键是启发式函数，好在对于路网的计算，可以直接拿两点之间的地理距离来构造启发式函数。
分别实现了这四个算法，并测试了它们的性能。其中Dijkstra's Algorithm的实现即是加了堆优化的版本，复杂度$O(|E| + |V| \log |V|)$。在解的质量上，A-star Algorithm和Dijkstra's Algorithm都能够求得最优解，而BFS和Greedy-BFS无法保证输出最优解；在运行耗时上，基本是：Greedy-BFS < A-star Algorithm < BFS < Dijkstra's Algorithm.

例如，计算节点`1-->150000`的最短路径（为了让耗时可比，选了网络上两个相距很远的节点），四个算法输出的路径长度和耗时分别是：

| 算法                   | 输出的路径长度 (m)   | 耗时 (s)   |
| -------------------- | ------------- | -------- |
| A-star Algorithm     | 120411.749686 | 0.295994 |
| Dijkstra's Algorithm | 120411.749686 | 1.063782 |
| Greedy BFS           | 144967.127015 | 0.017382 |
| BFS                  | 133310.682481 | 0.505906 |

到这里，基本上完成了底层路网的建图，接下来就是上层时空数据库的实现。

`2016.12.14-2016.12.15`

## spatio_temporal_index.py

对于时空索引，采用以Geo-Hash为*key*的Hash Map，*value*则存储我们所需要的相关信息，依据业务的不同自定义。Geo-Hash的编解码方法已经在`geohash.py`中实现。所以这里的重点是设计*value*的数据结构。

在T-Share的论文中，每个Grid主要维护三个表：

- spatially-ordered grid cell list
- temporally-ordered grid cell list
- taxi list sorted by the arrival time


这三个表都是有序的，其中，前两个是静态的，在路网初始化完成后就可以计算出来，第三个是动态的，在系统运行时会动态更新。因此前两个的数据结构可以选用Python中的`list`，最后一个选择heap。

在解释时空数据库的构建前，先就Geo-Hash的编码精度作一个简要说明。

### 关于Geo-Hash的编码精度

一个geo-hash就是一个网格的id，地理上的每个点都可以算出一个geo-hash（如果两个点的地理距离比较近，就会共享一个geo-hash，比如当geo-hash的长度为6时，每个网格的尺寸大概是`width * height = 1150m * 575m`）。

经过测试，在编码长度为6时，划出了12000多个网格，每个网格里的节点数很少，有5000多个网格里都只有一个节点（至少是一个节点），划分的粒度显得太细。编码长度取5时，划出了1163个网格，平均每个网格里有147个节点；只有一个节点的网格有30个，不算多；内部节点数超过1000的网格有37个；含有节点数最多的网格有2529个节点。所以编码长度取5比较合适。下图是编码长度取5时，网格内节点数量的分布情况。可见绝大部分网格里的节点数量都不超过500，极少数部分网格的节点数量超过1000，这些网格应该位于北京市的中心区域。

![grid_num_vertex](https://cl.ly/0H40013i1r3M/grid_num_vertex.png)

### 时空数据库的初始化

在路网加载完成后，就可以对时空数据库进行初始化，初始化完成后网格的数量、每个网格里有哪些节点就知道了。当然，还有一些信息是须要写成员方法去计算的，主要包括：

1. 确定一个网格的*anchor*
2. 计算*grid distance matrix*
3. 构建所有网格的*spatial grid list*和*temporal grid list*

下面分别解释做法。

#### 确定每个网格的*anchor*

按论文的做法来：

> We choose the road network node which is closest to the geographical center of the cell as the anchor node of the cell.

很方便的是，Geo-Hash解码的结果就是对应网格中心的位置（我开始怀疑论文里对于grid partition的做法是否就是Geo-Hash了，如果不是，我也觉得Geo-Hash比他们所采用的方法更好、更简单实用）。

所以，要确定一个网格的anchor，首先须要通过解码geo-hash算出该网格的中心点（可以在初始化一个网格的时候就计算出来），然后选择网格内距离中心点最近的节点作为该网格的anchor。如何找到最近的这个点？这是**平面最近点对**问题(the closest pair problem)，方老师在算法课讲分治算法的时候讲过。不过这里就没有必要用分治法了，因为不是找整个点集里的最近点对，而是到中心点的最近点，所以扫描一遍网格内所有的节点就行了。

#### 计算*grid distance matrix*

确定了每个grid cell的anchor之后，就可以计算grid distance matrix了。Grid distance matrix中的每个元素$D(i, j)$存储了ID为$i$的grid cell与ID为$j$的grid cell之间的时空距离信息，有两个字段：$d(i,j)$和$t(i,j)$, $d(i, j)$表示$grid(i)$到$grid(j)$的空间距离，$t(i, j)$表示$grid(i)$到$grid(j)$的时间距离。论文的计算方法是：

>We pre-compute the distance, denoted by $d(i, j)$, and travel time, denoted by $t(i, j)$, of the shortest path on the road network for each anchor node pair...since the traffic prediction is not a focus of this paper, we just use the speed limit of road segments to calculate travel time $t(i, j)$ for the sake of simplicity.

即$d(i, j)$是$grid(i)$的anchor到$grid(j)$的anchor之间的最短路径，而计算$t(i, j)$需要知道每条边的限速，但是由于获取的数据没有限速信息，所以我的处理方法如下：

- $d(i, j)$取$grid(i)$的anchor到$grid(j)$的anchor之间的地理距离（而不是最短路径）
- $t(i, j) = \frac{shortest\_path(i, j)}{average\_speed}$，其中$shortest\_path(i, j)$表示$grid(i)$的anchor到$grid(j)$的anchor之间最短路径的长度，$average\_speed$表示车辆的平均速度，比如取25 km/h（关于北京市不同区域的车辆平均速度的分布情况，可以参见[北京市交通委员会-交通指数](http://www.bjjtw.gov.cn/bmfw/jtzs/)）。

显然，这样算出来的grid distance matrix不是对称的，这也符合实际情况（因为路网是有向图）。本质上都是近似的方法。

计算的过程中出现的问题：

- 两个grid的anchor不可达。比如，id为107064的节点就在一个"孤岛"中。这时由于不存在最短路径，所以按原来的算法无法得到$t(i, j)$。处理方法是$t(i, j) = \frac{d(i, j)}{average\_speed}$.
- 计算所有点对之间最短路径的效率问题。虽然A-star算法可以很快地求出两点之间的最短路径，但是由于需要计算1000多个anchor node之间所有点对的最短路径（而且非对称），所以一共要计算$1000^2$次，即便跑一次A-star算法可以在0.01s内出结果，一百万次也要2.78个小时，时间还是太长。而[Floyd-Warshall algorithm](https://en.wikipedia.org/wiki/Floyd%E2%80%93Warshall_algorithm)虽然可以$O(|V|^3)$算出所有点对的最短路径，时间效率不错，但是$O(|V|^2)$的空间复杂度太高，如果运行在有17万个节点的图上，内存会爆掉（需要1000+GB的内存）。解决方法：以每个anchor node为单源跑Dijkstra算法，这样总共需要跑1000多次，一次大概1.2s，半小时左右可完成。更好的方法是算好后把数据写入文件，下次计算的时候通过文件读取进行初始化。


#### 为每个网格构建*spatial grid list*和*temporal grid list*

有了*grid distance matrix*之后，就可以着手计算*spatial grid list*和*temporal grid list*了。

以spatial grid list的构建为例，对于一个grid cell，首先定位到grid distance matrix中与其对应的行，依次取出该行中元素的spatial distance，并构建一个列表（Python中用`dict`存储），然后对该列表按spatial distance从小到大排序即可（用Python中的字典推导和lambda表达式可以很方便地完成这个任务）。

下面是测试的截图(如果图片看不清，大图在[这里](https://cl.ly/1k3e0b0D1d34))：

![spatio_temporal_list](https://cl.ly/1k3e0b0D1d34/snipaste20161216_153703.png)

打印了6个网格的相关信息，包括geo-hash, anchor的id, 含有的节点数量, spatial grid list和temporal grid list. 

到这里，时空索引的创建就基本完成了。至于*taxi list*，是在系统运行的过程中动态维护的，暂时不考虑其初始化，待开始设计taxi类之后再来解决这个问题。

`2016.12.16-2016.12.17`

## query.py

该模块主要实现乘客请求的抽象数据类型`Query`。

`Query`的基本属性有：

- `id` 一个请求的唯一标识。
- `timestamp` 乘客请求发出的时刻。
- `origin` 请求发出时乘客所在的位置，也是taxi去接乘客所要首先到达的位置。
- `destination` 乘客的目的地，也是taxi接到乘客以后所要到达的目的地。

除此之外，还有一些其他和业务需求有关的属性：

- 时间窗。有两个: `pickup_window`和`delivery_window`，分别对应接乘客和送达目的地这两个需求（的约束）。时间窗也可以定义成抽象类，包含两个属性：*early*和*late*，分别对应一个时间窗的开始时刻和结束时刻。

注：论文中没有为一个Query设定id，这是不合理的。Query相当于是对订单的建模，那么显然应该有一个唯一的标识，因为id对于实体实时状态的跟踪是必需的，起到索引的功能。

关于乘客须要做的信息输入，原文中的句子是：

> In practice, a passenger only needs to explicitly indicate $Q.d$ and $Q.wd.l$.

即乘客须要设定目的地和到达目的地的最晚时刻。我的认知是，**乘客其实只需要设定目的地**。因为时间窗这个东西对于乘客而言是不可改变的，而是由系统中的其他对象（司机、调度算法、路况等）所决定，而且在实际中，乘客也不太可能对时间窗有一个精确的估计，甚至连粗略的估计都不一定做到。如果一款打车APP要求乘客设定其到达目的地的时间窗，显然这样的要求会带来非常差的用户体验。作为乘客，只希望设定好目的地，然后就等待车来接送即可，而至于车什么时候能来接、以及多快能送到目的地，则是由系统的派车策略和调度算法决定的。

`Query`类也维护一些和模拟系统的运行、实验统计有关的信息：

- `matched_taxi`. 派车算法为该乘客所分配的taxi的id。
- `status`. 表征乘客的实时状态，主要有以下几个值：
  - `WAITING`. 乘客正在等待
  - `CANCELLED`. 乘客已经取消订单
  - `RIDING`. 乘客已经上车，正在路途中
  - `SATISFIED`. 乘客已经到达目的地
- `waiting_time`. 统计乘客在上车/取消订单前等待的时间。

### query数据读取

`query`模块也提供从文件读取query数据的函数: `load_query()`. 

数据来源于论文作者在项目主页提供的`TaxiQueryGenerator.jar`，运行该`.jar`包生成了47个`.txt`文件，每个文件里都存储着若干打车请求的数据。`load_query()`的功能即是依次读取这47个文件，构造`Query`实例，然后存入请求队列，为仿真系统的运行提供驱动。一条请求数据有如下四个字段：

| 字段                            | 含义     |
| ----------------------------- | ------ |
| `QUERY_BIRTH_TIME`            | 请求生成时刻 |
| `QUERY_ORIGIN_LATITUDE`       | 出发地的纬度 |
| `QUERY_ORIGIN_LONGITUDE`      | 出发地的经度 |
| `QUERY_DESTINATION_LATITUDE`  | 目的地的纬度 |
| `QUERY_DESTINATION_LONGITUDE` | 目的地的经度 |

读完所有47个文件用时20秒，一共有325545条用户打车请求数据。由于文件中的数据并不是严格按照时间顺序生成，所以存放所有请求的容器选用优先队列（以时间戳为优先级）。

读文件时遇到的问题及解决方法：

- 如何批量读取文件？可以使用Python内置的`os`模块。示例如下：

```python
import os

file_list = os.listdir("./data/queries")  # 获取目录下的所有文件名，存入列表
for file_name in file_list:  # 依次读取文件
    cur_file = open("./data/queries/" + file_name)  # 打开文件
    # 做一些事情
    # ...
    cur_file.close()  # 关闭文件
```

- 在进行字符串处理时涉及到日期转换以及相关的计算，使用Python提供的`datetime`类可以较好地完成这一任务。如，如何把字符串`"15:23:55"`转换成一天内累计的第几秒（int类型）？比如，`"00:00:00"`是一天的第1秒，`"00:00:01"`是第2秒，`"00:00:05"`是第6秒，...，`"23:59:59"`是第86400秒。示例做法如下：

```python
from datetime import datetime

str = '15:23:55'
time1 = datetime.strptime(str, '%H:%M:%S')  # 利用datetime.strptime()把字符串转换为日期类型
start_time = datetime.strptime('00:00:00', '%H:%M:%S')  # 同时构造一个开始时刻
delta_time = (time1 - start_time).seconds + 1  # 将两个变量相减即可
```

## taxi.py

该模块主要实现taxi的抽象数据类型`Taxi`。

`Taxi`的基本属性有：

- `id`. 一辆taxi的唯一标识。
- `location`.  taxi的实时位置。
- `num_riders`. taxi的实时乘客数量。
- `schedule`. taxi要陆续到达的地理位置序列。引导taxi的行驶路线，也和时空数据库的*taxi list*有关。论文中的描述：

> A *schedule* is a temporally-ordered sequence of pickup and delivery points of $n$ queries $Q_1, Q_2, \ldots, Q_n$ such that for every query $Q_i, i = 1,..., n$, either 1) $Q_i.o$ precedes $Q_i.d$ in the sequence, or 2) only $Q_i.d$ exists in the sequence.

这是一个动态维护的序列，里面放的是taxi要依次到达的`Location`，如序列的第一个元素就是taxi当前所要去的位置。每当taxi到达一个预定的位置时，就把该位置从序列的头部删除；每当系统将taxi与新的乘客进行匹配时，就要涉及到把乘客的起点和目的地插入这个序列以检查可行性的操作（插入的位置不一定在序列的尾部）。所以该序列的数据结构选择链表比较合适，但是考虑到序列的size很小（因为一辆taxi通常也就能容纳4名乘客，所以size不会超过10），于是就不用纠结于数据结构的选择了，用Python的`list`即可。

- `route`. taxi当前在路网上的路径规划方案，根据`schedule`计算得来。也就是taxi到`schedule`序列的第一个位置的路径。数据类型使用`road_network`模块中定义的`Path`.

`Taxi`类也维护一些和模拟系统的运行、实验统计有关的信息：

- `query_list`. 当前该taxi正在服务的Query列表，里面存放的是Query的id。显然这是一个需要动态维护的数据结构，每当有新乘客上车时，就将该乘客/query的id加入；每当有乘客下车时，就将相应的query删除。由于taxi的容量很小，所以数据结构就选用`list`.
- `e_id`. 当前该taxi所在的路段（边）的id。
- `driving_distance`. 当前该taxi已经行驶的距离。


### taxi数据生成

类似于query，也必须要有taxi实体。

taxi实体的数据不像query那么难生成，因为query是要从taxi的轨迹数据中学习的（否则自己随机生成很容易脱离实际情况），而taxi则没有这么严格的要求，只要数量和初始位置设置得合理即可。

taxi的数量就取论文实验的设定: **2980**.

taxi初始位置的设定是难点。我采用的方法是：根据时空数据库的网格内的节点分布情况来设定该区域所放置的taxi的初始状态。具体而言是：一个网格初始的taxi数量与网格内的节点数量成比例，而taxi的初始位置就位于节点上。这样的设置是合理的，因为如果一个网格里的节点数量很多，意味着道路比较密集，路口比较多，越接近市中心，相应的打车需求也应该较多，所以taxi也应该多。每个网格内taxi的数量计算如下:

$$一个网格内的{taxi}数量 = round \left ( \frac{该网格内节点数量}{节点总量} \times {taxi}总量 \right ).$$

其中, $round()$表示四舍五入取整。另外，由于taxi总量远远小于节点总量，所以网格内taxi的数量小于网格内节点数量，因此至少可以把一个taxi安放在一个没有放置过taxi的节点上。

### *taxi list*的初始化

生成taxi数据后，就可以对时空数据库每个网格的*taxi list*进行初始化了（之前只初始化了*spatially-ordered grid cell list*和*temporally-ordered grid cell list*）。

taxi list记录的是所有即将进入一个网格$grid(i)$的taxi的ID，并且附带记录它们具体会在什么时刻$t_a$进入该网格。所有的taxi按$t_a$从早到晚排序。所以这是一个须要动态维护的表：

- 当一个taxi离开$grid(i)$时，就将其从表里删除
- 当一个taxi的schedule中新加入了$grid(i)$时，就将其加入该表
- 如果一个taxi改变了其schedule（该情况发生在系统为该taxi匹配了新乘客的时候，这时须要更新该taxi的schedule），则要对该taxi会进入的所有网格的taxi list做相应的更新（主要更新进入时刻）。

一直比较纠结taxi list数据结构的选择，因为该表涉及到插入、删除、以及按优先级遍历的操作。目前的选择是`dict`，以taxi的ID为key，以时间戳$t_a$为value. 不过这样taxi不是按$t_a$有序组织的，需要的话全部扫描一遍应该也可以接受。

初始化时，所有的taxi对应的时间戳是仿真系统的开始时刻，意思是在仿真开始时taxi就已经到达该网格了。

初始化完成后，含有最多taxi数量的网格内有44辆，不算多。

`2016.12.21-2016.12.22`

## dispatcher.py

该模块主要为系统的派车功能提供服务接口。其主要任务是响应`Query`实体，为其分配最佳的taxi。

主要有两个部分：

- taxi searching: 筛选出所有满足时间窗约束（乘客等待时间约束）的taxi.
- taxi scheduling: 在上一步的基础上进一步做*insertion feasibility check*并在满足约束的taxis中选出additional travel distance最短的.

下面分别解释算法。

### taxi searching

Taxi searching的算法步骤如下：

1. 首先定位到query所在的网格, 设该网格为$grid(i)$.
2. 扫描$grid(i)$的*temporally-ordered grid cell list*, 筛选出所有满足时间窗约束（时间距离小于query最长等待时间）的网格.
3. 考察上一步中筛选出的每一个网格的taxi list，将所有满足时间窗约束的taxi加入备选列表.

### taxi scheduling

Taxi scheduling是比较难的一个问题。也是派车/拼车最核心的问题，即具体地考察请求与某一辆候选taxi的匹配程度，并把请求的地点和目的地插入taxi的原路径规划方案中。

### 其他遇到的问题和解决方法

- `Query`实例的`origin`和`destination`往往不太可能正好落在路网的节点上，这样在进行*taxi searching*时就无法计算它们到其他节点的最短路径。
  - 解决方法：这属于所谓的**map-matching problem**. 我们须要把一个query的出发地和目的地映射到路网的节点或者边上。比较精确的做法应该是把query的起终点映射到周围与其匹配度最高的边上，然后计算一个offset (其与边起点或终点的距离)。为了简单起见，我的做法是直接将其映射到周围与其最近的节点上。具体地，和之前确定一个网格的anchor的方法一样，即扫描一遍所在网格内的所有节点，选出距离最短的。
  - 效果：我的做法很有效，算出来的映射点与query的出发地、目的地的距离差基本都在**50m**以内。两个地点匹配的绝对距离的分布情况见下图（上面的是出发地，下面的是目的地）。
    ![ori_dis](https://cl.ly/1U1S00162m0k/origin_dis.png)
    ![des_dis](https://cl.ly/293x45194612/destination_dis.png)
  - 可能存在的问题：由于对每个query的`origin`和`destination`都要扫描一遍其所在网格的所有节点，当query数量很多时，程序的效率很低：处理100个query就要1秒多，而`TaxiQueryGenerator`一共生成了一天的请求数据（有**325545**条），处理完估计至少需要1个小时。不过由于simulation的时间段并不是全天，没有必要加载所有的query。论文中取的时间段是`9:00am-9:30am`，一共1800秒，筛选出来不超过10000条，只对这10000条query做*map-matching*的话速度会快得多。

`2016.12.23-2016.12.24`

在给query匹配了最佳的taxi以后，taxi就应该按照系统的调度来接送乘客。所以，一个重要的问题就是，**如何模拟一辆taxi在路网上的运动**？为此，在`Taxi`类中新添加一个成员方法`drive()`来抽象这一过程。

## Taxi的drive()方法

从high level逻辑来看，一辆taxi的运动会对动态系统中的哪些对象/变量产生影响？

- 因为taxi运动了，产生了位移，直接地，其地理位置会改变；
- taxi的运动是有目的的，运动将会使得其到达一个乘客的等待地点，接乘客上车；也会使得其到达一个乘客的下车地点，让乘客下车；
- taxi的运动会改变时空数据库的存储信息。

首要问题是：如何计算出经过一个时间步长后taxi的新位置？

### 位置更新

这其实是一个物理问题。如果要知道一辆车经过一段时间后新的状态，我们需要哪些条件？应该是：车的初始状态，以及其运动方式。具体地，是：初始时车的位置、速度、方向，以及车的运动形式的完整描述（匀速还是变速、直线还是曲线等）。为此，做如下假设：

- 将车看做质点
- 车做匀速直线运动

如果是在平面上，使用平面直角坐标系可以很容易地解决这个问题（三维的空间直角坐标系同理）。设车初始位置是$(x_0, y_0)$, 车的速度是$v$, 与$x$轴正方向的夹角是$\theta$. 那么经过$t$时间, 车的位置可以用下式计算:
$$
\begin{cases}
& x = x_0 + v \cdot \cos{\theta}, \\ 
& y = y_0 + v \cdot \sin{\theta}, \\
\end{cases}
$$

如果是采用经纬度的球面坐标系呢? 设我们现在知道车的速度和位置(纬度, 经度), 方向怎么表示? 用方向角(bearing/heading/direction angel). **两个地理位置之间方向角的计算**, 以及**给定初始位置、方向角和距离, 计算另一个位置的方法**见[这里](http://www.igismap.com/formula-to-find-bearing-or-heading-angle-between-two-points-latitude-longitude/) (这篇教程写得很清楚), 方向角的可视化应用见[这里](http://gistools.igismap.com/bearing).

### 位置检查和触发更新

解决位置更新的计算方法后，回到我们的模拟场景中。既然计算方向角需要两个地理坐标，如果我们知道taxi当前的坐标，另一个坐标怎么获取？我的方法是在`Taxi`类中新添加一个成员变量`e_id`，以维护目前taxi所在的边，这样就知道了taxi是朝着路网上的哪个节点行驶（因为是有向边），于是就可以据此计算方向角。该成员变量的动态更新依据taxi的当前位置和路由信息（`Taxi.route`），接下来会解释。

Taxi不可能一直都沿着直线在一条路上行驶，而是在路网上运动，所以总会转弯或者经过某个路口，从而进入下一条路段（边）。如果到了一条边的终点，就需要做相应的状态更新（比如所在的边）。那么问题就是：**如何判断taxi是否已经行驶到一条边的终点**？

我的做法是：计算taxi当前位置与所在边的起点的距离(offset)，将其与边的长度做比较。如果比边的长度长，就说明已经过了边的终点，否则说明还在这条边上行驶。由于时间步长取得比较短(1秒)，因此超过的距离不会很多（顶多几米），所以如果发现已经过了边的终点，新的位置就取边的终点。

当taxi到达边的终点后，会触发状态更新。有两种情况：
- 到达的终点是一条路径的**中间某条边**的终点（后续还有边），这时更新taxi所在边即可；
- 到达的终点是一条路径的**最后一条边**的终点（后续没有边），这时说明到达了其当前schedule中所要到达的下一个`ScheduleNode`（即到了某个query的出发地或目的地），因此触发如下更新：
  - 根据所到达的`ScheduleNode`的情况做出相应的动作：
    - 如果是某个query的出发地：先检查该query的`status`，看其是否已经取消。如果没有，让该query “上车”，即修改该query的`status`为`RIDING` (已经上车)，并将query添加到taxi的成员变量`Taxi.serving_queries`中；如果已经取消，就把`schedule`中与该query有关的`ScheduleNode`删除.
    - 如果是某个query的目的地：说明该query成功完成。让该query “下车”，即修改该query的`status`为`SATISFIED` (已经完成)，并在`Taxi.serving_queries`中删除该query.
    - 接着，根据`Taxi.schedule`的下一个`ScheduleNode`重新计算`route`。如果没有下一个`ScheduleNode`了，说明已经到了最后一个目的地并且系统没有为该taxi派单，这时就将`route`置为`None`；否则调用最短路径算法计算当前所处节点到下一个`ScheduleNode`的最短路径（由于做*map-matching*时是将query的origin和destination都映射到附近的节点上，所以此时taxi一定处于某个节点上），并赋值给`route`.
    - 然后，根据上一步计算好的`route`更新时空数据库的*taxi list*. 具体的方法在下面一小节解释。

### 时空数据库的更新

时空数据库中需要动态维护的信息是每个网格的*taxi list*:

> Taxi $V_j$ is removed from the list when $V_j$ leaves $g_i$; taxi $V_k$ is inserted into the list when $V_k$ is newly scheduled to enter $g_i$.

即当一辆taxi离开某个网格时，要将taxi从该网格的taxi list中删除；当一辆taxi的schedule中加入某个新的要进入的网格时，要将taxi插入该网格的taxi list.

taxi list中元素的删除。可以在*位置更新*的同时检查一辆taxi是否改变了其geo-hash，从而判断该taxi是否离开了某个网格，这时就更新离开网格的taxi list（同时也可以更新进入网格的taxi list）。

taxi list中元素的插入。这个相比删除要困难一些，因为要插入的是未来某个时刻会进入某个网格的taxi。我的思路是在`Taxi.route`被重新计算的时候做这项工作。所以只是根据taxi下一个要去的目的地的最短路径进行了到达时间估计（ETA），并没有对更远的目的地做ETA。这么做有好有坏，如下是我对这种做法考虑到的影响：

- 一个缺点是比较明显的，即ETA预测得不够远。对于拼车的情形，一辆taxi往往会有好几个目的地要依次到达，而我的做法仅仅是根据第一个要到达的地点更新时空数据库。这样会使得距离该taxi比较远的网格的taxi list中没有该taxi的记录（即便该taxi会在未来进入这个网格），从而影响taxi searching时可行解的数量，如果第一个目的地很近，可能会导致可行解过少。
- 优点：计算简单。只在`Taxi.route`被更新时计算，所以不存在反复更新的问题。反复更新的问题在预测多个目的地的ETA做法中是存在的，因为如果有一个新的乘客被安排在未来加入一辆taxi，就要把该乘客的起点和目的地插入该taxi的schedule，从而使得taxi的schedule中该乘客起点之后所有目的地的ETA都要被重新计算。由于每计算一个目的地的ETA就要调用多次最短路径算法，这样可能导致计算开销很大。

具体的更新方法：当`Taxi.route`被重新计算后，就扫描`Taxi.route`的节点（recall that the data type of `Taxi.route` is `Path`, 这些节点就是该taxi即将陆续到达的节点），找到第一个geo-hash发生改变的节点，同时记录taxi从route的起点到该点的时间（路程除以速度），更新其所在网格的taxi list；然后再找到下一个geo-hash发生改变的节点并更新其所在网格的taxi list，以此类推。

`2016.12.25-2016.12.26`

## simulation.py

Simulation的主程序。

事件(query)是主要的驱动力，时间推进模式采用按时间步长(1秒)推进。在一个时间步长内，主要的事件和系统中各对象的动作逻辑：

1. query发生
2. 系统对query做出响应
   1. 如果超过query最长等待时间，取消query，否则
   2. 为query派车，包含
      1. taxi searching
      2. taxi scheduling
   3. 如果没有找到可用的taxi, 把该query放入一个队列，在下一轮时间步长再处理
3. 所有taxi按schedule行驶。会发生以下三种情况：
   - 普通行驶
   - taxi到达query发出点
   - taxi到达query目的地

`2016.12.27`

测试主程序，解决了一些bug，目前的问题是`Taxi.drive()`可能存在实现上没考虑到的问题，正在定位问题。

`2016.12.28-2016.12.29`

### Taxi Ridesharing Simulation的测试

昨天的问题是当主程序开始运行后，出现“taxi永远都到不了乘客那儿”的现象。原因无非是：

- Taxi根本没有连接时空数据库
- `Taxi.drive()`实现上有问题，使得taxi根本没有真正“运动”起来

检查代码时，在`Simulation`的`__init__()`方法中发现一个低级错误（成员变量赋值），这个疏忽，使得时空数据库没有做动态信息的初始化。

定位到的另外一个重大的问题在于**整数截断**。这是使得“taxi不运动”的主要原因。主要问题在于`constants.py`中一些常量的设置。taxi平均速度和地球平均半径的写法分别是：`AVERAGE_SPEED = 7`, `R = 6371 * 10**3` ，这样使得程序在运行时，这两个量被Python解释器当做整数处理，于是所有的运算都采用整数运算，导致发生了截断，达不到地理计算所需要的精度。正确的写法应该是：`AVERAGE_SPEED = 7.0`, 以及`R = 6371.0 * 10**3`.

以上问题修复以后，仿真系统的运行看起来比较正常了，至少taxi开始运动，有pick-up和drop-off事件发生了。但是存在以下问题：

- 绝大部分乘客都取消了订单。一共9727条query，有9668条都被取消。

原因可能有：

- 乘客的*pickup window*设置得不合理
- taxi的数量设置得不合理
- taxi的初始分布设置得不合理
- 调度算法的问题

因为之前为了尽快地测试系统，taxi的容量设为1（即*Non-Ridesharing*的机制），调度算法的*taxi searching*和*taxi scheduling*部分都只用了一个贪心算法草草了事。以上的原因，前两条都是和论文设置得一致，最后两条更有可能。接下来先从修改调度算法开始尝试。

#### Non-Ridesharing

调整了算法以后（还是*Non-Ridesharing*的情形），被取消的订单降到了8073条，按论文的说法，*Satisfaction Rate*大概是$(9727 - 8073) / 9727 = 0.17$. 虽然取消率还是很高，不过这和论文的结果差不多，说明不拼车的机率是很低的。

- 乘客的最长等待时间由5分钟增加到10分钟: ${Satisfaction Rate} = \frac{9727 - 6368}{9727} = 34.53 \%$.
- 乘客的最长等待时间设为15分钟: ${Satisfaction Rate} = \frac{9727 - 4816}{9727} = 50.49 \%$.

`2017.03.02`

对于taxi仿真的初始化慢问题，今天和老师讨论了一下，要么自己编一个小图，要么对原始数据预处理一下，要么只取原始数据的一部分（也就是一个连通子图）。其实三个方法都是可行的，要说困难的话，就是编小图需要费一番脑筋保证数据至少不会太离谱，取子图以及预处理则要修改读数据的代码。本以为预处理原始数据会比较麻烦，因为涉及到文件的读写和数据结构的重构，思考一番后，发现这就是**数据结构的序列化和反序列化**问题，在网络传输中是不可缺少的技术。自己写序列化和反序列化当然也行，只是代码量可能比较大，因为这相当于是自己设计一个传输协议了，有时候重复造轮子是不可取的，想着Python应该有相应的库函数来做这件事，果然Python没有让我失望，Google很快就有了答案：

http://python3-cookbook.readthedocs.io/zh_CN/latest/c05/p21_serializing_python_objects.html

也就是加几行代码的事情。

结果是：初始化最耗时的部分由半个小时降到50秒左右了。