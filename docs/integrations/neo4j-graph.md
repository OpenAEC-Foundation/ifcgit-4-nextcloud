# Neo4j Graph Database Integration

## Overview

The Neo4j integration stores IFC model data as a property graph, enabling:

- **Spatial queries** -- traverse building hierarchy (Site > Building > Storey > Space > Elements)
- **Type lookups** -- find all elements of a given IFC class
- **Relationship exploration** -- visualize how entities connect (containment, aggregation, type definitions, property sets)
- **Visual graph exploration** -- interactive force-directed graph in the browser
- **Large model support** -- Neo4j handles 40GB+ models efficiently via indexed graph traversal

## Architecture

```
IFC File (uploaded via Git)
       |
       v
  IFC Parser (ifcopenshell)
       |
       v
  Neo4j Graph Database
       |
    ┌──┴──────────────────┐
    |                     |
    v                     v
 Graph API          Graph Viewer
 (FastAPI)          (Canvas/Force)
```

### Node Schema

Each IFC entity with a GlobalId becomes a Neo4j node:

| Property     | Type   | Description                          |
|-------------|--------|--------------------------------------|
| `global_id` | String | IFC GlobalId (unique constraint)     |
| `ifc_class` | String | IFC class name (e.g. `IfcWall`)      |
| `name`      | String | Entity name                          |
| `description` | String | Entity description                 |
| `project_id` | String | Project slug for data isolation      |
| `ifc_id`    | Int    | Entity ID within the IFC file        |

Nodes also receive a dynamic label matching their IFC class (e.g. `:IfcWall`, `:IfcSlab`).

### Relationship Types

| Relationship   | IFC Source                             | Meaning                          |
|---------------|----------------------------------------|----------------------------------|
| `CONTAINED_IN` | `IfcRelContainedInSpatialStructure`   | Element is in a space/storey     |
| `PART_OF`      | `IfcRelAggregates`                    | Child is part of parent          |
| `DEFINED_BY`   | `IfcRelDefinesByProperties`           | Element has a property set       |
| `HAS_TYPE`     | `IfcRelDefinesByType`                 | Element is of a certain type     |

## Setup

### 1. Enable Neo4j in Docker Compose

Set the environment variable in your `.env` file:

```env
NEO4J_ENABLED=true
NEO4J_USER=neo4j
NEO4J_PASSWORD=neo4j-ifcgit
```

Then start the stack:

```bash
docker compose up -d
```

Neo4j Browser is available at `http://localhost:7474` for direct Cypher queries.

### 2. Import an IFC File

After uploading an IFC file to a project, trigger the graph import:

```bash
# Via API
curl -X POST "http://localhost:8080/api/projects/my-project/graph/import?file_path=model.ifc" \
  -H "Authorization: Bearer $TOKEN"
```

Or use the Graph Explorer UI in the project view.

### 3. Explore the Graph

Navigate to **Project > Graph Explorer** (graph icon in the sidebar) to visualize the model.

## API Endpoints

All graph endpoints are mounted under `/api/projects/{slug}/graph/`.

### GET `/api/projects/{slug}/graph/data`

Get nodes and edges for visualization.

**Query Parameters:**
| Parameter   | Type   | Default | Description                    |
|------------|--------|---------|--------------------------------|
| `ifc_class` | string | null   | Filter by IFC class            |
| `depth`     | int    | 2      | Traversal depth (1-5)          |
| `limit`     | int    | 200    | Maximum number of nodes        |

**Response:**
```json
{
  "nodes": [
    {
      "id": "2O2Fr$t4X7Z...",
      "label": "Ground Floor",
      "ifc_class": "IfcBuildingStorey",
      "name": "Ground Floor",
      "group": "storey"
    }
  ],
  "edges": [
    {
      "source": "2O2Fr$t4X7Z...",
      "target": "3vB2Y$t4X7Z...",
      "type": "CONTAINED_IN"
    }
  ]
}
```

### GET `/api/projects/{slug}/graph/stats`

Get graph statistics.

**Response:**
```json
{
  "node_count": 1234,
  "relationship_count": 5678,
  "class_distribution": [
    { "ifc_class": "IfcWall", "count": 342 },
    { "ifc_class": "IfcSlab", "count": 128 }
  ],
  "relationship_distribution": [
    { "type": "CONTAINED_IN", "count": 800 },
    { "type": "PART_OF", "count": 200 }
  ]
}
```

### GET `/api/projects/{slug}/graph/node/{global_id}`

Get a specific entity and its neighbors.

**Query Parameters:**
| Parameter | Type | Default | Description            |
|----------|------|---------|------------------------|
| `depth`   | int  | 1      | Neighbor depth (1-3)   |

### GET `/api/projects/{slug}/graph/search`

Search entities by name, class, or description.

**Query Parameters:**
| Parameter | Type   | Default | Description           |
|----------|--------|---------|-----------------------|
| `q`       | string | required | Search query          |
| `limit`   | int    | 50      | Maximum results       |

### POST `/api/projects/{slug}/graph/import`

Import an IFC file into the graph database.

**Query Parameters:**
| Parameter    | Type   | Description                    |
|-------------|--------|--------------------------------|
| `file_path`  | string | Path to IFC file in project    |

## Graph Visualization

The Graph Explorer provides an interactive force-directed graph:

- **Pan** -- Click and drag on the background
- **Zoom** -- Mouse wheel
- **Select** -- Click a node to see its properties
- **Expand** -- Double-click a node to load its neighbors
- **Filter** -- Use the class dropdown to show only specific IFC types
- **Search** -- Find entities by name or class

### Visual Groups (Color Coding)

| Group      | Color   | IFC Classes                              |
|-----------|---------|------------------------------------------|
| site      | Green   | IfcSite                                  |
| building  | Blue    | IfcBuilding                              |
| storey    | Cyan    | IfcBuildingStorey                        |
| space     | Teal    | IfcSpace                                 |
| wall      | Orange  | IfcWall, IfcWallStandardCase            |
| slab      | Brown   | IfcSlab, IfcRoof                        |
| structural| Red     | IfcColumn, IfcBeam, IfcMember           |
| opening   | Purple  | IfcWindow, IfcDoor                      |
| mep       | Pink    | IfcPipe, IfcDuct, IfcFlowTerminal      |
| property  | Gray    | IfcPropertySet, IfcQuantitySet          |
| type      | Yellow  | IfcWallType, IfcSlabType, etc.          |

## Example Cypher Queries

Access Neo4j Browser at `http://localhost:7474` to run custom queries:

```cypher
-- Find all walls on the ground floor
MATCH (wall:IfcWall)-[:CONTAINED_IN]->(storey:IfcBuildingStorey)
WHERE storey.name CONTAINS 'Ground'
RETURN wall.name, storey.name

-- Show the full building hierarchy
MATCH path = (site:IfcSite)<-[:PART_OF*]-(child)
WHERE site.project_id = 'my-project'
RETURN path LIMIT 100

-- Count elements per storey
MATCH (el:IfcEntity)-[:CONTAINED_IN]->(storey:IfcBuildingStorey)
WHERE el.project_id = 'my-project'
RETURN storey.name, count(el) AS element_count
ORDER BY element_count DESC

-- Find elements sharing a property set
MATCH (a:IfcEntity)-[:DEFINED_BY]->(pset)<-[:DEFINED_BY]-(b:IfcEntity)
WHERE a.project_id = 'my-project' AND a <> b
RETURN a.name, b.name, pset.name LIMIT 20
```

## Configuration

| Environment Variable | Default              | Description              |
|---------------------|----------------------|--------------------------|
| `NEO4J_ENABLED`     | `false`              | Enable Neo4j integration |
| `NEO4J_URI`         | `bolt://neo4j:7687`  | Neo4j Bolt URI           |
| `NEO4J_USER`        | `neo4j`              | Neo4j username           |
| `NEO4J_PASSWORD`    | `neo4j-ifcgit`       | Neo4j password           |
