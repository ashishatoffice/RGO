import rdflib
from rdflib.namespace import RDF, RDFS, OWL
import os
import owlready2
import tempfile

# Global cache for graphs
_ASSERTED_GRAPH = None
_INFERRED_GRAPH = None

def load_graph(inferred=False):
    global _ASSERTED_GRAPH, _INFERRED_GRAPH
    
    
    # Path to ontology
    ontology_path = r'd:/ashish/webapp/ritualgrammar_marriage/ontology/ritualgrammar.ttl'
    print("Graph Loaded")
    # Load asserted graph if not loaded
    if _ASSERTED_GRAPH is None:
        _ASSERTED_GRAPH = rdflib.Graph()
        # Parse using rdflib for the asserted view
        _ASSERTED_GRAPH.parse(ontology_path, format='turtle')
        
    if not inferred:
        return _ASSERTED_GRAPH
        
    # Load/Compute inferred graph if not loaded
    if _INFERRED_GRAPH is None:
        print("Computing inferences with HermiT (via owlready2)... this may take a moment.")
        
        # Bridge: RDFLib (Turtle) -> RDF/XML -> Owlready2
        # We process the graph to remove external imports that cause parsing errors (e.g., getting HTML instead of RDF)
        
        # Create a temporary graph to strip imports
        g_for_inference = rdflib.Graph()
        for triple in _ASSERTED_GRAPH:
            # Skip owl:imports assertions to prevent auto-fetching
            if triple[1] == OWL.imports:
                continue
            g_for_inference.add(triple)

        # FORCE Transitivity for P9, P10i, and broader hierarchy properties so Owlready2 picks it up
        crm = rdflib.Namespace("http://www.cidoc-crm.org/cidoc-crm/")
        skos = rdflib.Namespace("http://www.w3.org/2004/02/skos/core#")

        # FORCE Transitivity for P9, P10i, and broader hierarchy properties so Owlready2 picks it up
        crm = rdflib.Namespace("http://www.cidoc-crm.org/cidoc-crm/")
        skos = rdflib.Namespace("http://www.w3.org/2004/02/skos/core#")

        # Define them as ObjectProperty AND TransitiveProperty to be safe for ALL reasoners
        # Also ensure P2_has_type is an ObjectProperty for the chain
        targets_transitive = [crm.P9_consists_of, crm.P10i_contains, crm.P10_falls_within, crm.P9i_forms_part_of, skos.broader, crm.P127_has_broader_term]
        for prop in targets_transitive:
            g_for_inference.add((prop, RDF.type, OWL.ObjectProperty))
            g_for_inference.add((prop, RDF.type, OWL.TransitiveProperty))
            
        g_for_inference.add((crm.P2_has_type, RDF.type, OWL.ObjectProperty))
        
        # LINK P9 and P10i for Mixed Transitivity
        # By making P9 (consists of) a subProperty of P10i (contains), 
        # a chain like A -P10i-> B -P9-> C becomes A -P10i-> B -P10i-> C
        # Since P10i is transitive, this infers A -P10i-> C.
        g_for_inference.add((crm.P9_consists_of, RDFS.subPropertyOf, crm.P10i_contains))
        g_for_inference.add((crm.P9i_forms_part_of, RDFS.subPropertyOf, crm.P10_falls_within))
        
        # Create a temporary file for the RDF/XML representation
        with tempfile.NamedTemporaryFile(suffix='.rdf', delete=False) as tmp:
            g_for_inference.serialize(destination=tmp.name, format='xml')
            tmp_path = tmp.name
            
        try:
            # Load logic using Owlready2
            world = owlready2.World()
            # Use file URI protocol
            onto = world.get_ontology(f"file://{tmp_path}").load()
            
            # Add Property Chain via Owlready2 API (Safer than manual RDF/XML injection)
            # P2_has_type o broader -> P2_has_type
            try:
                # Retrieve the properties from the loaded world
                p2 = next(world.sparql("""SELECT ?p WHERE { ?p <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/2002/07/owl#ObjectProperty> . FILTER(STR(?p) = 'http://www.cidoc-crm.org/cidoc-crm/P2_has_type') }"""))[0]
                broader = next(world.sparql("""SELECT ?p WHERE { ?p <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/2002/07/owl#ObjectProperty> . FILTER(STR(?p) = 'http://www.w3.org/2004/02/skos/core#broader') }"""))[0]
                
                # Define property chain: has_type o broader implies has_type
                p2.property_chain.append(owlready2.PropertyChain([p2, broader]))
            except Exception as e:
                print(f"Warning: Could not enable property chain inference: {e}")
            
            # Run HermiT reasoner
            owlready2.sync_reasoner(world, infer_property_values=True)
            
            print("Inference complete. Converting to RDFLib graph...")
            
            # We need to bridge back to RDFLib. 
            _INFERRED_GRAPH = world.as_rdflib_graph()
            
            # Bind the namespaces from the asserted graph for convenience (prefixes)
            for prefix, namespace in _ASSERTED_GRAPH.namespaces():
                _INFERRED_GRAPH.bind(prefix, namespace)
                
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        
    return _INFERRED_GRAPH

def get_navigation_structure(inferred=False):
    g = load_graph(inferred=inferred)
    
    crm = rdflib.Namespace("http://www.cidoc-crm.org/cidoc-crm/")
    skos = rdflib.Namespace("http://www.w3.org/2004/02/skos/core#")
    
    entities = {}
    
    def get_label(entity_uri):
        alt_label = g.value(entity_uri, skos.altLabel)
        if alt_label: return str(alt_label)
        pref_label = g.value(entity_uri, skos.prefLabel)
        if pref_label: return str(pref_label)
        label = g.value(entity_uri, RDFS.label)
        if label: return str(label)
        return str(entity_uri).split('#')[-1]

    # Pre-scan entities that have labels
    labeled_entities = set()
    for s in g.subjects(unique=True):
        if (s, skos.altLabel, None) in g or (s, skos.prefLabel, None) in g or (s, RDFS.label, None) in g:
            labeled_entities.add(s)
            entities[s] = {'id': str(s), 'label': get_label(s), 'children': [], 'parents': []}
           
    # relevant_predicates
    relevant_predicates = {
        crm.P10_falls_within, crm.P9i_forms_part_of, 
        crm.P10i_contains, crm.P9_consists_of,
        skos.broader, crm.P127_has_broader_term
        
    }
    
    for s, p, o in g:
        if p in relevant_predicates:
            if s not in labeled_entities or o not in labeled_entities:
                continue
                
            is_parent_child_direction = (p == crm.P10i_contains or p == crm.P9_consists_of)
            parent = s if is_parent_child_direction else o
            child = o if is_parent_child_direction else s
            
            if child not in entities[parent]['children']:
                entities[parent]['children'].append(entities[child])
            if parent not in entities[child]['parents']:
                entities[child]['parents'].append(entities[parent])
    
    # Standard Root Finding (No strict filtering, restoring original behavior)
    roots = []
    for s, data in entities.items():
        if not data['parents'] and data['children']:
             roots.append(data)
    
    # Fallback
    if not roots:
        for s, data in entities.items():
            if data['children']:
                roots.append(data)

    # Serialize
    def serialize(node, visited=None):
        if visited is None: visited = set()
        if node['id'] in visited:
            return {'id': node['id'], 'label': node['label'], 'children': []}
        visited.add(node['id'])
        
        children_list = []
        for child in node['children']:
             children_list.append(serialize(child, visited.copy()))
        
        children_list.sort(key=lambda x: x['label'])
             
        return {
            'id': node['id'],
            'label': node['label'],
            'children': children_list
        }
    unique_roots = {}
    for root in roots:
        unique_roots[root["id"]] = root

   
    
    serialized_roots = [serialize(root) for root in roots]
    
    return serialized_roots

def get_event_navigation_structure(inferred=False):
    # We need both graphs:
    # Inferred: To find the Events (which might be inferred) and their connection to Types (P2).
    # Asserted: To traverse the Type Hierarchy (skos:broader) without transitive shortcuts.
    g_inferred = load_graph(inferred=True)
    g_asserted = load_graph(inferred=False)
    
    crm = rdflib.Namespace("http://www.cidoc-crm.org/cidoc-crm/")
    skos = rdflib.Namespace("http://www.w3.org/2004/02/skos/core#")
    rg_ritual = rdflib.URIRef("https://www.ritualgrammar.org/ontology/Ritual")
    
    # 1. Identify all Events from Inferred Graph
    target_events = set(g_inferred.subjects(RDF.type, crm.E5_Event))
    
    tree_map = {} # parent_uri -> set(child_uri)
    nodes_data = {} # uri -> {'id': ..., 'label': ...}
    
    def get_label(entity_uri, g_source):
        alt = g_source.value(entity_uri, skos.altLabel)
        if alt: return str(alt)
        pref = g_source.value(entity_uri, skos.prefLabel)
        if pref: return str(pref)
        lbl = g_source.value(entity_uri, RDFS.label)
        if lbl: return str(lbl)
        return str(entity_uri).split('#')[-1]

    # Pre-populate Root
    nodes_data[str(rg_ritual)] = {'id': str(rg_ritual), 'label': get_label(rg_ritual, g_asserted), 'children': []}
    #print(nodes_data[str(rg_ritual)])
    relationships = set()
    
    for event in target_events:
        # Get all types of this event (Inferred)
        all_types = set(g_inferred.objects(event, crm.P2_has_type))
        if not all_types: continue
        
        # 2. Filter for Most Specific Types only
        # Strategy: If T1 is broader than T2, we discard T1. 
        # But we must check this relationship in the Inferred Graph where broader logic is complete.
        
        most_specific_types = set(all_types)
        for t1 in all_types:
            for t2 in all_types:
                if t1 == t2: continue
                # if t2 is narrower than t1 (i.e., t2 has broader t1)
                # In Inferred graph, this triple (t2, broader, t1) exists transitively
                if (t2, skos.broader, t1) in g_inferred:
                    if t1 in most_specific_types:
                        most_specific_types.remove(t1)

        # 3. Build Tree upward from Specific Types using ASSERTED hierarchy
        event_str = str(event)
        nodes_data[event_str] = {'id': event_str, 'label': get_label(event, g_inferred), 'children': [], 'is_event': True}
        
        for leaf_type in most_specific_types:
            leaf_str = str(leaf_type)
            
            # Link Event to Leaf Type
            if (leaf_str, event_str) not in relationships:
                relationships.add((leaf_str, event_str))
                if leaf_str not in tree_map: tree_map[leaf_str] = set()
                tree_map[leaf_str].add(event_str)
            
            if leaf_str not in nodes_data:
                nodes_data[leaf_str] = {'id': leaf_str, 'label': get_label(leaf_type, g_asserted), 'children': []}

            # Traverse Up strictly using Asserted Graph to avoid flatten shortcuts
            curr = leaf_type
            queue = [curr]
            visited_up = set()
            
            while queue:
                ct = queue.pop(0)
                if ct == rg_ritual: continue
                ct_str = str(ct)
                
                if ct_str in visited_up: continue
                visited_up.add(ct_str)
                
                # Get Asserted Parents
                parents = list(g_asserted.objects(ct, skos.broader))
                
                for p in parents:
                    p_str = str(p)
                    
                    # Store Node Data
                    if p_str not in nodes_data:
                        nodes_data[p_str] = {'id': p_str, 'label': get_label(p, g_asserted), 'children': []}
                    
                    # Store Link
                    if (p_str, ct_str) not in relationships:
                        relationships.add((p_str, ct_str))
                        if p_str not in tree_map: tree_map[p_str] = set()
                        tree_map[p_str].add(ct_str)
                    
                    queue.append(p)

    # 4. Serialize from Root
    def build_tree(node_id, visited):
        if node_id in visited: return None
        visited.add(node_id)
        
        node = nodes_data.get(node_id)
        if not node: return None
        
        children_ids = tree_map.get(node_id, set())
        children_list = []
        for child_id in children_ids:
            child_tree = build_tree(child_id, visited.copy())
            if child_tree:
                children_list.append(child_tree)
        
        # Sort children by label
        children_list.sort(key=lambda x: x['label'])
        
        return {
            'id': node['id'],
            'label': node['label'],
            'children': children_list,
            'is_event': node.get('is_event', False)
        }
    
    root_tree = build_tree(str(rg_ritual), set())
    
    if root_tree:
        return [root_tree]
    return []

def execute_sparql_query(query_string, inferred=False):
    g = load_graph(inferred=inferred)
    try:
        results = g.query(query_string)
        
        # Parse results into a friendly format
        output = []
        # JSON-like structure: columns and rows
        
        # If it's a SELECT query
        if results.type == 'SELECT':
            vars = [str(v) for v in results.vars]
            rows = []
            for row in results:
                # Create an ordered list of cells matching 'vars'
                row_list = []
                for v in vars:
                    val = row[v]
                    if val is not None:
                        str_val = str(val)
                        is_uri = isinstance(val, rdflib.URIRef)
                        
                        # Compute label
                        label = str_val
                        if is_uri:
                            # Try to find RDFS label
                            rdfs_label = g.value(val, RDFS.label)
                            if rdfs_label:
                                label = str(rdfs_label)
                            elif '#' in str_val:
                                label = str_val.split('#')[-1]
                            else:
                                label = str_val.split('/')[-1]
                        
                        row_list.append({
                            'value': str_val,
                            'label': label,
                            'type': 'uri' if is_uri else 'literal'
                        })
                    else:
                        row_list.append(None)
                rows.append(row_list)
            return {'type': 'SELECT', 'vars': vars, 'results': rows}
        
            return {'type': 'SELECT', 'vars': vars, 'results': rows}
        
        # Handle Graph results (DESCRIBE, CONSTRUCT)
        if results.type == 'DESCRIBE' or results.type == 'CONSTRUCT':
            vars = ['Subject', 'Predicate', 'Object']
            rows = []
            for s, p, o in results:
                row_list = []
                for val in [s, p, o]:
                    if val is not None:
                        str_val = str(val)
                        is_uri = isinstance(val, rdflib.URIRef)
                        
                        # Compute label
                        label = str_val
                        if is_uri:
                            rdfs_label = g.value(val, RDFS.label)
                            if rdfs_label:
                                label = str(rdfs_label)
                            elif '#' in str_val:
                                label = str_val.split('#')[-1]
                            else:
                                label = str_val.split('/')[-1]
                        
                        row_list.append({
                            'value': str_val,
                            'label': label,
                            'type': 'uri' if is_uri else 'literal'
                        })
                    else:
                        row_list.append(None)
                rows.append(row_list)
            return {'type': 'TRIPLES', 'vars': vars, 'results': rows}

        return {'type': 'OTHER', 'results': 'Query type not supported for table view.'}
        
    except Exception as e:
        return {'error': str(e)}

# Helper to explore details of a node
def get_node_details(node_id, inferred=False):
    g = load_graph(inferred=inferred)
    node_uri = rdflib.URIRef(node_id)
    details = {'id': node_id, 'properties': []}
    
    seen = set()  # (predicate, object, direction)

    ignored_types = {str(OWL.NamedIndividual), str(OWL.Class), str(OWL.ObjectProperty),
                     str(OWL.DatatypeProperty), str(OWL.Ontology), str(OWL.AnnotationProperty),
                     "http://www.w3.org/2004/02/skos/core#Concept"}
    ignored_predicates = {str(OWL.imports), str(OWL.versionIRI)}

    # Outgoing
    for p, o in g.predicate_objects(subject=node_uri):
        key = (str(p), str(o), 'out')
        if key in seen:
            continue
        seen.add(key)

        if str(p) in ignored_predicates or (p == RDF.type and str(o) in ignored_types):
            continue

        p_label = g.value(p, RDFS.label) or (str(p).split('#')[-1] if '#' in str(p) else str(p).split('/')[-1])
        o_label = str(o)
        if isinstance(o, rdflib.URIRef):
            o_label = g.value(o, RDFS.label) or (str(o).split('#')[-1] if '#' in str(o) else str(o).split('/')[-1])

        details['properties'].append({
            'predicate': str(p),
            'predicate_label': str(p_label),
            'object': str(o),
            'object_label': str(o_label),
            'is_uri': isinstance(o, rdflib.URIRef),
            'direction': 'out'
        })
    '''
    # Incoming
    for s, p in g.subject_predicates(object=node_uri):
        key = (str(p), str(s), 'in')
        if key in seen:
            continue
        seen.add(key)

        if str(p) in ignored_predicates:
            continue

        p_label = g.value(p, RDFS.label) or (str(p).split('#')[-1] if '#' in str(p) else str(p).split('/')[-1])
        s_label = str(s)
        if isinstance(s, rdflib.URIRef):
            s_label = g.value(s, RDFS.label) or (str(s).split('#')[-1] if '#' in str(s) else str(s).split('/')[-1])
        p_label = f"'{p_label}' of"

        details['properties'].append({
            'predicate': str(p),
            'predicate_label': p_label,
            'object': str(s),
            'object_label': s_label,
            'is_uri': isinstance(s, rdflib.URIRef),
            'direction': 'in'
        })
    '''
    return details

