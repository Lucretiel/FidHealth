from collections import namedtuple
from functools import wraps


def unroll(t):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return t(func(*args, **kwargs))
        return wrapper
    return decorator


def copay(amount):
    return lambda cost: min(cost, amount)


def coinsure(percent):
    mult = percent / 100
    return lambda cost: cost * mult


def covered():
    return lambda cost: 0


def not_covered():
    return lambda cost: cost

class OfferedService(namedtuple('OfferedService',
        ('type', 'ignore_deductible'))):
    '''
    OfferedService represents data about a service offered by a single plan.
    For instance, in-network PCP.

    type is a function which, when called with a price, returns the updated
    price under the plan. This mod is called *after* the deductible is met, and
    before the out-of-pocket max is met. This is a function which modifies the
    price correctly. The assumption is that, before deductible, the user is
    paying 100%, and after out of pocket max, they are paying 0%.

    If ignore_deductible is True, the mod should be applied right away to the
    cost of the service.
    '''
    def __new__(mod=not_covered(), ignore_deductible=False):
        return super().__new__(cls, mod, ignore_deductible)


class LiteralService(namedtuple('LiteralService',
        ('cost', 'mod', 'ignore_deductible'))):
    '''
    LiteralService is the internal representation of a service requested by a
    user. It is generated by combining a Service with an Offered service. This
    is the object used to actually perform the calculations.
    '''
    @classmethod
    def create(requested_service, offered_service):
        '''
        Combine a requested_service and an offered_service
        '''
        return cls(
            requested_service.cost,
            offered_service.type.mod,
            offered_service.ignore_deductible)


class Service(namedtuple('Service', ('name', 'cost', 'in_network'))):
    '''
    A Service represents a service requested by a user.

    `cost` is the "sticker price" of the service.
    `in_network` is the
    '''
    def __new__(cls, type, cost, in_network=True):
        return super().__new__(cls, type, cost, in_network)


def apply_to_threshold(threshold, cost):
    '''
    Given some maximum cumulative threshold, apply a cost to the threshold.
    Returns the amount applied to the threshold, the remaining value of the
    threshold, and any overflow to the cost.

    Examples:

    100, 10 -> 10, 90, 0
    60, 100 -> 60, 0, 40
    '''
    from_max = min(threshold, cost)
    return from_max, threshold - from_max, cost - from_max


def threshold_overflow(threshold, cost):
    '''
    Perfom an apply_to_threshold, returning the new threshold and the overflow.
    Discard the amount applied to the threshold
    '''
    return apply_to_threshold(threshold, cost)[1:3]


def at_threshold(threshold, cost):
    '''
    Perform an apply_to_threshold, returning the amount applied and the
    remaining value of the threshold. Discard the overflow.
    '''
    return apply_to_threshold(threshold, cost)[0:2]


class NetworkSimResult(namedtuple('NetworkSimResult',
        ('out_of_pocket', 'deductible', 'oop_maximum'))):
    '''
    The result of a individual network simulation. Contains the amount paid,
    the remaining deductible, and the remaining out of pocket maximum.
    '''


class SimResult(namedtuple('SimResult',
        ('out_of_pocket', 'services', 'premiums', 'hsa_remaining'))):
    '''
    The result of a simulation for a whole plan.

    out_of_pocket is the total amount paid
    services is the total amount paid for services, not including premiums
    premiums is the total amount paid for just premiums
    hsa_remaining is the amount remaining in the hsa.
    '''


class NetworkDetails:
    '''
    Network details manages all the services for a given plan for a given
    network. A plan brings together two networks- in network and out-of-network-
    as well as some global details like monthy premium
    '''
    def __init__(self, deductible, out_of_pocket_max, services, in_network):
        self.deductible = deductible
        self.out_of_pocket_max = out_of_pocket_max
        self.services = services
        self.in_network = in_network

    def service_list(self):
        return self.services.keys()

    def get_service(self, service_name):
        return self.services.get(service_name, OfferedService())

    def run_sim(self, services):
        deductible = self.deductible
        oop_maximum = self.out_of_pocket_max
        year_out_of_pocket = 0

        for service in services:
            if isinstance(service, Service):
                if service.in_network != self.in_network:
                    continue

                service = LiteralService.create(
                    service,
                    self.get_service(service.name))

            if not service.ignore_deductible:
                # Apply the deductible
                # `pre_deduct` is the amount applied to the deductible.
                # `deductible` is the remaining deductible
                # `cost` is any remaining cost after the deductible
                pre_deduct, deductible, cost = apply_to_threshold(
                    deductible,
                    service.cost)

                # Update the out of pocket maximum
                # `pocket_cost` is the amount allowed by the out of pocket max.
                # `oop_maximum` is the remaining out of pocket maximum
                pocket_cost, oop_maximum = at_threshold(
                    oop_maximum,
                    pre_deduct)
                year_out_of_pocket += pocket_cost

            # Apply the mod (coinsurance or copay) to the cost after or
            # ignoring or applying the deductible, then apply the out of pocket
            # maximum
            # `pocket_cost` is the amount allowed by the out of pocket max
            # `oop_maximum` is the remaining out of pocket maximum
            pocket_cost, oop_maximum = at_threshold(
                oop_maximum,
                service.mod(cost))
            year_out_of_pocket += pocket_cost

        return SimResult(year_out_of_pocket, deductible, oop_maximum)


class Plan:
    '''
    Plan manages a single plan- HDHP, POS, etc.
    '''
    def __init__(self, premium, hsa_contribution, in_network, out_of_network):
        self.premium = premium
        self.hsa_contribution = hsa_contribution
        self.in_network = in_network
        self.out_of_network = out_of_network

    @unroll(set)
    def service_list(self):
        for network in self.in_network, self.out_of_network:
            for service in network.service_list():
                yield service

    def convert_services(self, services, network):
        '''
        Given all the services in a year, filter to only the services on this
        network, and convert to the literal (cost, mod, ignore_deductible)
        format
        '''
        for service in services:
            if service.in_network == network.in_network:
                yield LiteralService.create(
                    service, network.get_service(service.name))

    def run_sim(self, services, months=12):
        services = tuple(services)

        in_network = self.in_network.run_sim(
            self.convert_services(services, self.in_network))
        out_of_network = self.out_of_network.run_sim(
            self.convert_services(services, self.out_of_network))

        hsa = self.hsa_contribution

        hsa, out_of_pocket = threshold_overflow(hsa,
            in_network.out_of_pocket + out_of_network.out_of_pocket)

        return SimResult(
            out_of_pocket,
            )


global_service_names = {
    'er': 'Emergency Room',
    'pcp': 'Primary Care Physician'
}


class GlobalServices:
    def __init__(self):
        self.plans = None

    def load_plans(self):
        self.plans = {
            'POS': Plan(
                premium=55,
                hsa_contribution=0,
                in_network=NetworkDetails(
                    deductible=0,
                    out_of_pocket_max=1500,
                    in_network=True,
                    services={
                        'er': OfferedService(copay(75)),
                        'pcp': OfferedService(copay(15))
                    }),
                out_of_network=NetworkDetails(
                    deductible=1000,
                    out_of_pocket_max=1500,
                    in_network=False,
                    services={
                        'er': OfferedService(copay(75)),
                        'pcp': OfferedService(coinsure(20))
                    })),
            'HDHP': Plan(
                premium=15,
                hsa_contribution=625,
                in_network=NetworkDetails(
                    deductible=1500,
                    out_of_pocket_max=2500,
                    in_network=True,
                    services={}),
                out_of_network=NetworkDetails(
                    deductible=2500,
                    out_of_pocket_max=5000,
                    in_network=False,
                    services={}))}

    @unroll(set)
    def get_service_list(self):
        for plan in self.plans.values():
            for service in plan.service_list():
                yield global_service_names.get(service, service), service


services = GlobalServices()
load_plans = services.load_plans
get_service_list = services.get_service_list
