from sensor_app.models import Device, FluidBag
from django.core.cache import cache

CACHE_TIMEOUT = 60 * 10 


def get_device(node_id):
    key = f'device:{node_id}'
    device = cache.get(key)
    if device is None:
        device = Device.objects.get(id = node_id, type='node')
        cache.set(key, device, CACHE_TIMEOUT)
    return device

def get_fluid_bag(device):
    key = f'fluidbag:{device.id}'
    fluid_bag = cache.get(key)
    if fluid_bag is None:
        fluid_bag = FluidBag.objects.filter(device=device).filter()
        cache.set(key, fluid_bag, CACHE_TIMEOUT)
    return fluid_bag