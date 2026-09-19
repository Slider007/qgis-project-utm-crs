def classFactory(iface):
    from .plugin import ProjectUtmCrsPlugin
    return ProjectUtmCrsPlugin(iface)
