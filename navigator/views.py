from django.shortcuts import render, HttpResponse
from django.http import JsonResponse
from .graph_utils import get_navigation_structure, get_node_details, execute_sparql_query

def landing_page(request):
    return render(request, 'navigator/landing.html')

def navigation_view(request):
    inferred = request.GET.get("inferred", "true").lower() == "false"

    roots = get_navigation_structure(inferred=inferred)

    return render(request, "navigator/navigation.html", {
        "roots": roots,
        "inferred": inferred, 
    })

def inferred_navigation_view(request):

    inferred = request.GET.get("inferred", "true").lower() == "true"

    roots = get_navigation_structure(inferred=inferred)

    return render(request, "navigator/navigation.html", {
        "roots": roots, 
        "inferred": inferred
        })


def events_navigation_view(request):
    from .graph_utils import get_event_navigation_structure
    roots = get_event_navigation_structure(inferred=True)
    return render(request, 'navigator/navigation.html', {'roots': roots, 'mode': 'Events by Rituals ' })

def sparql_view(request):
    default_query = 'SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 50'
    query = request.POST.get('query') or request.GET.get('query') or default_query
    results = None
    
    inferred = request.GET.get('inferred') == 'true'
    
    if request.method == 'POST' or request.GET.get('run'):
        results = execute_sparql_query(query, inferred=inferred)
        
    return render(request, 'navigator/sparql.html', {'results': results, 'query': query, 'inferred': inferred})

def node_details(request):
    node_id = request.GET.get('id')
    inferred = request.GET.get('inferred') == 'true'
    print("Inference flag in view:", inferred)
    if not node_id:
        return JsonResponse({'error': 'No id provided'}, status=400)
    data = get_node_details(node_id, inferred=inferred)
    
    return JsonResponse(data)

