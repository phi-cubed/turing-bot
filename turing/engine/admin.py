from django.contrib import admin
from .models import *
from simple_history.admin import SimpleHistoryAdmin
from django.contrib.auth.admin import UserAdmin

class ListDisplayGara:
    @admin.display(description='Nome gara', ordering='gara__nome')
    def get_nome_gara(self, obj):
        return obj.gara.nome

    @admin.display(description='ID gara', ordering='gara__pk')
    def get_id_gara(self, obj):
        return obj.gara.pk

class GaraFilter(admin.SimpleListFilter):
    parameter_name = "gara__pk"
    title = "Gara"

    def lookups(self, request, model_admin):
        """Generate the list of choices."""
        gare = Gara.objects.all().order_by("-id")
        return [(gara.pk, f"{gara.nome}, ID {gara.pk}") for gara in gare]

    def queryset(self, request, queryset):
        """Filter the queryset by the selected value"""
        value = self.value()
        if value is not None:
            return queryset.filter(gara__pk=value)
        return queryset

class SquadraFilter(admin.SimpleListFilter):
    parameter_name = "squadra__pk"
    title = "Squadra"

    def lookups(self, request, model_admin):
        """Generate the list of choices."""
        gara_pk = request.GET.get("gara__pk", None)
        if gara_pk is None:
            squadre = Squadra.objects.all()
        else:
            squadre = Squadra.objects.filter(gara__pk=gara_pk)
        squadre = squadre.order_by("id")
        return [
            (
                squadra.pk,
                f"{squadra.num:02d} - {squadra.nome}, ID {squadra.pk}" + (
                    f", della gara {squadra.gara.nome}" if gara_pk is None else "")
            ) for squadra in squadre
        ]

    def queryset(self, request, queryset):
        """Filter the queryset by the selected value"""
        value = self.value()
        if value is not None:
            return queryset.filter(squadra__pk=value)
        return queryset

class ProblemaFilter(admin.SimpleListFilter):
    parameter_name = "problema"
    title = "Problema"

    def lookups(self, request, model_admin):
        """Generate the list of choices."""
        gara_pk = request.GET.get("gara__pk", None)
        if gara_pk is None:
            soluzioni = Soluzione.objects.all()
        else:
            soluzioni = Soluzione.objects.filter(gara__pk=gara_pk)
        soluzioni = soluzioni.order_by("id")
        return [
            (
                soluzione.problema,
                f"{soluzione.problema:02d} - {soluzione.nome}, ID {soluzione.pk}" + (
                    f", della gara {soluzione.gara.nome}" if gara_pk is None else "")
            ) for soluzione in soluzioni
        ]

    def queryset(self, request, queryset):
        """Filter the queryset by the selected value"""
        value = self.value()
        if value is not None:
            return queryset.filter(problema=value)
        return queryset

class GaraAdmin(admin.ModelAdmin):
    list_display = ('pk', 'nome', 'inizio')
    list_display_links = ('pk', 'nome')

admin.site.register(Gara, GaraAdmin)

class SquadraAdmin(admin.ModelAdmin, ListDisplayGara):
    list_display = ('pk', 'get_nome_gara', 'get_id_gara', 'num', 'nome')
    list_display_links = ('pk', 'num', 'nome')
    list_filter = (GaraFilter, )

admin.site.register(Squadra, SquadraAdmin)

class SoluzioneAdmin(admin.ModelAdmin, ListDisplayGara):
    list_display = ('pk', 'get_nome_gara', 'get_id_gara', 'problema', 'nome')
    list_display_links = ('pk', 'problema', 'nome')
    list_filter = (GaraFilter, )

admin.site.register(Soluzione, SoluzioneAdmin)

class ConsegnaAdmin(SimpleHistoryAdmin, ListDisplayGara):
    list_display = ('pk', 'get_nome_gara', 'get_id_gara', 'squadra', 'problema', 'risposta', 'orario')
    list_display_links = ('pk', 'squadra', 'problema')
    list_filter = (GaraFilter, SquadraFilter, ProblemaFilter)
    readonly_fields = ('orario', )

admin.site.register(Consegna, ConsegnaAdmin)

class JollyAdmin(SimpleHistoryAdmin, ListDisplayGara):
    list_display = ('pk', 'get_nome_gara', 'get_id_gara', 'squadra', 'problema', 'orario')
    list_display_links = ('pk', 'squadra', 'problema')
    list_filter = (GaraFilter, SquadraFilter, ProblemaFilter)
    readonly_fields = ('orario', )

admin.site.register(Jolly, JollyAdmin)

class BonusAdmin(SimpleHistoryAdmin, ListDisplayGara):
    list_display = ('pk', 'get_nome_gara', 'get_id_gara', 'squadra', 'punteggio', 'orario')
    list_display_links = ('pk', 'squadra')
    list_filter = (GaraFilter, SquadraFilter)
    readonly_fields = ('orario', )

admin.site.register(Bonus, BonusAdmin)

class MyUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'gender', 'is_staff')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Informazioni personali', {'fields': ('first_name', 'last_name', 'email', 'gender')}),
        ('Permessi', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Date importanti', {'fields': ('last_login', 'date_joined')}))

admin.site.register(User, MyUserAdmin)

class SystemSettingsAdmin(admin.ModelAdmin):
    filter_horizontal = ('allowed_users',)

admin.site.register(SystemSettings, SystemSettingsAdmin)
