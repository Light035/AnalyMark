from django.core.paginator import Paginator


def paginate(request, queryset, parameter="page", per_page=20):
    raw = request.GET.get(parameter, "1")
    # No huge integer parsing, negative indexes or arbitrary page sizes.
    number = int(raw) if raw.isascii() and raw.isdecimal() and len(raw) <= 8 and int(raw) > 0 else 1
    return Paginator(queryset, per_page).get_page(number)
