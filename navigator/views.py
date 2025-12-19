from django.shortcuts import render, HttpResponse
from django.http import JsonResponse
from .graph_utils import get_navigation_structure, get_node_details, execute_sparql_query

def landing_page(request):
    return render(request, 'navigator/landing.html')

def navigation_view(request):
    structure = get_navigation_structure()
    return render(request, 'navigator/navigation.html', {'structure': structure})

def sparql_view(request):
    default_query = 'SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 50'
    query = request.POST.get('query') or request.GET.get('query') or default_query
    results = None
    
    if request.method == 'POST' or request.GET.get('run'):
        results = execute_sparql_query(query)
        
    return render(request, 'navigator/sparql.html', {'results': results, 'query': query})

def node_details(request):
    node_id = request.GET.get('id')
    if not node_id:
        return JsonResponse({'error': 'No id provided'}, status=400)
    data = get_node_details(node_id)
    return JsonResponse(data)

