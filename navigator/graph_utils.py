import rdflib
from rdflib.namespace import RDF, RDFS, OWL
import os

def load_graph():
    g = rdflib.Graph()
    # Path validity needs to be handled. Assuming the current structure.
    # The ontology file is in d:/ashish/webapp/ritualgrammar_marriage/ontology/ritualgrammar.ttl
    ontology_path = r'd:/ashish/webapp/ritualgrammar_marriage/ontology/ritualgrammar.ttl'
    g.parse(ontology_path, format='turtle')
    return g

def get_navigation_structure():
    g = load_graph()
    crm = rdflib.Namespace("http://www.cidoc-crm.org/cidoc-crm/")
    
    # Relationships for parent -> child
    # P10i_contains: Parent contains Child
    # P9_consists_of: Parent consists of Child
    # P148_has_component: Parent has component Child (sometimes used)
    
    # Relationships for child -> parent
    # P10_falls_within: Child falls within Parent
    # P9i_forms_part_of: Child forms part of Parent
    
    structure = {}
    nodes = {}
    entities = {}
    
    # Initialize all entities with a label
    for s, p, o in g:
        if p == RDFS.label:
            if s not in entities: entities[s] = {'id': str(s), 'label': str(o), 'children': [], 'parents': []}
            else: entities[s]['label'] = str(o)
            
    # Ensure all subjects/objects in relevant triples exist in entities dict
    relevant_predicates = {
        crm.P10_falls_within, crm.P9i_forms_part_of, # Child -> Parent
        crm.P10i_contains, crm.P9_consists_of       # Parent -> Child
    }
    
    for s, p, o in g:
        if p in relevant_predicates:
            if s not in entities: entities[s] = {'id': str(s), 'label': str(s).split('#')[-1].split('/')[-1], 'children': [], 'parents': []}
            if o not in entities: entities[o] = {'id': str(o), 'label': str(o).split('#')[-1].split('/')[-1], 'children': [], 'parents': []}
            
            if p == crm.P10i_contains or p == crm.P9_consists_of:
                # s is parent, o is child
                if entities[o] not in entities[s]['children']:
                    entities[s]['children'].append(entities[o])
                if entities[s] not in entities[o]['parents']:
                    entities[o]['parents'].append(entities[s])
            else:
                # s is child, o is parent
                if entities[s] not in entities[o]['children']:
                    entities[o]['children'].append(entities[s])
                if entities[o] not in entities[s]['parents']:
                    entities[s]['parents'].append(entities[o])

    # Find roots
    # A root is something that has children but no parents (or parents are not in the set of events we care about)
    roots = []
    for s, data in entities.items():
        if not data['parents'] and data['children']:
             roots.append(data)
    
    # If no obvious roots, just take anything with children
    if not roots:
        for s, data in entities.items():
            if data['children']:
                roots.append(data)

    # Unique roots check
    final_roots = []
    seen = set()
    for r in roots:
        if r['id'] not in seen:
            final_roots.append(r)
            seen.add(r['id'])

    # Prepare a JSON-serializable structure
    def serialize(node, visited=None):
        if visited is None: visited = set()
        if node['id'] in visited:
            return {'id': node['id'], 'label': node['label'], 'children': []} # Break cycle
        visited.add(node['id'])
        
        # Determine strict children (ones that point back to this node as parent)
        # We already built the tree based on explicit relations.
        
        children_list = []
        for child in node['children']:
             children_list.append(serialize(child, visited.copy()))
             
        return {
            'id': node['id'],
            'label': node['label'],
            'children': children_list
        }
        
    serialized_roots = [serialize(root) for root in final_roots]
    return serialized_roots

def execute_sparql_query(query_string):
    g = load_graph()
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
def get_node_details(node_id):
    g = load_graph()
    node_uri = rdflib.URIRef(node_id)
    details = {'id': node_id, 'properties': []}
    
    # Axioms/Boilerplate to filter out or simplify
    ignored_types = {
        str(OWL.NamedIndividual), 
        str(OWL.Class),
        str(OWL.ObjectProperty),
        str(OWL.DatatypeProperty),
        str(OWL.Ontology),
        str(OWL.AnnotationProperty)
    }

    ignored_predicates = {
        str(OWL.imports),
        str(OWL.versionIRI)
    }
    
    for p, o in g.predicate_objects(subject=node_uri):
        p_str = str(p)
        o_str = str(o)
        
        # Filter unwanted properties
        if p_str in ignored_predicates:
            continue
            
        # Filter specific types (boilerplate)
        if p == RDF.type and o_str in ignored_types:
            continue
            
        # Resolve Label for Predicate
        p_label = p_str
        p_rdfs = g.value(p, RDFS.label)
        if p_rdfs:
            p_label = str(p_rdfs)
        else:
             # Fallback nice formatting for standard known namespaces could go here
             if '#' in p_str: p_label = p_str.split('#')[-1]
             else: p_label = p_str.split('/')[-1]

        # Resolve Label for Object (if URI)
        o_label = o_str
        if isinstance(o, rdflib.URIRef):
             o_rdfs = g.value(o, RDFS.label)
             if o_rdfs:
                 o_label = str(o_rdfs)
             elif '#' in o_str:
                 o_label = o_str.split('#')[-1]
             else:
                 o_label = o_str.split('/')[-1]
        
        details['properties'].append({
            'predicate': p_str,
            'predicate_label': p_label,
            'object': o_str,
            'object_label': o_label,
            'is_uri': isinstance(o, rdflib.URIRef)
        })
        
    return details
