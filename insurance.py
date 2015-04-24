from functools import wraps
from decimal import Decimal
from itertools import tee
from functools import wraps
from collections import namedtuple

def _apply(result_type):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return result_type(func(*args, **kwargs))
        return wrapper
    return decorator


def apply_to_threshold(threshold, cost):
    '''
    Given some maximum cumulative threshold, apply a cost to the threshold.
    Returns the amount applied to the threshold, the remaining value of the
    threshold, and any overflow to the cost.
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


class LiteralService(namedtuple('LiteralService', ('cost', 'mod', 'ignore_deductible'))):
    def __new__(cls, cost, mod, ignore_deductible=False):
        return super().__new__(cls, cost, mod, ignore_deductible)


class Service(namedtuple('Service', ('name', 'cost', 'in_network'))):
    def __new__(cls, type, cost, in_network=True):
        return super().__new__(cls, type, cost, in_network)

    def as_literal_service(self, plan_details):
        details = plan_details.get(self.name, not_covered())

        if isinstance(details, tuple):
            mod, ignore_deductible = details
        else:
            mod, ignore_deductible = details, False

        return LiteralService(self.cost, mod, ignore_deductible)


NetworkState = namedtuple('NetworkState',
    ('month_total', 'year_total', 'deductible', 'oop_maximum'))


PlanState = namedtuple('PlanState', (
    'month_total', 'month_service', 'year_total', 'year_service',
    'coverage_remaining', 'in_network_state', 'out_of_network_state'))


def network_tracker(network_deductible, network_oop_maximum):
    '''
    Create a generator that tracks health service costs for a period of months.
    It tracks the deductible, out of pocket maximum, and out of pocket costs,
    month by month. The generated should be called with a list of months, where
    each month is a list of literal services.

    The generator iterates through the service months, yielding the state each
    month. The state consists of a tuple of:

        - The amount paid this month
        - The amount paid thus far over the year
        - The remaining deductible
        - The remaining out of pocket maximum

    This function is designed to track the costs for a deductible/oop/etc for
    a single kind of network (in-network/out-of-network). See plan_tracker,
    below, for a function that tracks in and out together, and see plan_sim for
    a function that also handles the service types.

    Note that this function creates the generator function- it's essentailly
    a template, so that the same plan can be reused.
    '''
    def tracker(service_months):
        deductible = network_deductible
        oop_maximum = network_oop_maximum

        year_out_of_pocket = 0

        for services in service_months:
            month_out_of_pocket = 0

            for cost, mod, ignore_deductible in services:
                # Handle the deductible
                if not ignore_deductible:
                    # Apply the deductible
                    # `pre_deduct` is the amount applied to the deductible.
                    # `deductible` is the remaining deductible
                    # `cost` is any remaining cost after the deductible
                    pre_deduct, deductible, cost = apply_to_threshold(deductible, cost)

                    # Apply the out of pocket maximum
                    # `pocket_cost` is the amount allowed by the out of pocket max
                    # `oop_maximum` is the remaining out of pocket maximum
                    pocket_cost, oop_maximum = at_threshold(oop_maximum, pre_deduct)
                    month_out_of_pocket += pocket_cost

                # Apply the mod (coinsurance or copay) to the cost after or ignoring
                # the deductible, then apply the out of pocket maximum
                # `pocket_cost` is the amount allowed by the out of pocket max
                # `oop_maximum` is the remaining out of pocket maximum
                pocket_cost, oop_maximum = at_threshold(oop_maximum, mod(cost))
                month_out_of_pocket += pocket_cost

            # Apply this month's costs to the total
            year_out_of_pocket += month_out_of_pocket

            # Yield the state after the current month
            yield NetworkState(
                month_out_of_pocket,
                year_out_of_pocket,
                deductible,
                oop_maximum)

    return tracker


def plan_tracker(premium, plan_employer_contribution,
      in_network_init, out_of_network_init):
    '''
    This creates a generator for a full plan. `in_network_init` and
    `out_of_network_init` are each tuples of (deductible, out_of_pocket_max)
    for the two network types. It creates a generator which can be called with
    two separate service years- one for the in-network services and one for the
    out of network-services. See `network_tracker` for details in this. It
    yields the current state each month:
        - The amount paid this month (including the premium)
        - The amount paid thus far in the year
        - The remaining amount of employer coverage
        - The in-network state
        - The out-of-network state

    Note that, like `network_tracker`, this function creates a generator
    function, which is called with the service years to create a generator for
    the simulation.
    '''
    in_network = network_tracker(*in_network_init)
    out_of_network = network_tracker(*out_of_network_init)

    def tracker(in_network_services, out_of_network_services):
        employer_contribution = plan_employer_contribution
        year_out_of_pocket = 0
        year_service_cost = 0

        for in_network_state, out_of_network_state in zip(
                in_network(in_network_services),
                out_of_network(out_of_network_services)):

            # Check employer contribution coverage.
            employer_contribution, month_service_cost = threshold_overflow(
                employer_contribution,
                (in_network_state[0] + out_of_network_state[0]))

            # Update with the premium
            month_out_of_pocket = month_service_cost + premium

            # Update the yearly total
            year_out_of_pocket += month_out_of_pocket
            year_service_cost += month_service_cost

            yield PlanState(
                month_out_of_pocket, month_service_cost,
                year_out_of_pocket, year_service_cost,
                employer_contribution,
                in_network_state,
                out_of_network_state)

    return tracker


def plan_sim(
      premium, employer_contribution,
      in_network_service_details, out_of_network_service_details):
    '''
    Wrapper for plan_tracker to dispatch services. in_network_services and
    out_of_network_services are dicts of each service category, where each is
    made up of (mod, ignore deductible). The inits and premium are passed
    directly to plan_tracker. This function should be sent services, which are
    a tuple of:
        - service name
        - service cost
        - in network

    It yields out the same state as plan_tracker
    '''

    def convert_services(service_months, in_network, details):
        '''
        Given all the services in a year, filter to only the services on this
        network, and convert to the literal (cost, mod, ignore_deductible)
        format
        '''
        for services in service_months:
            yield [service.as_literal_service(details)
                for service in services
                if service.in_network == in_network]


    in_network_init = (
        in_network_service_details['deductible'],
        in_network_service_details['out_of_pocket_max'])

    out_of_network_init = (
        out_of_network_service_details['deductible'],
        out_of_network_service_details['out_of_pocket_max'])

    tracker = plan_tracker(premium, employer_contribution,
        in_network_init, out_of_network_init)

    def sim(service_months):
        in_service_months, out_of_service_months = tee(service_months)

        for state in tracker(
            convert_services(in_service_months, True, in_network_service_details),
            convert_services(out_of_service_months, False, out_of_network_service_details)):

            yield state

    return sim


def copay(amount):
    return lambda cost: min(cost, amount)


def coinsure(percent):
    mult = percent / 100
    return lambda cost: cost * mult


def covered():
    return lambda cost: 0


def not_covered():
    return lambda cost: cost

@_apply(tuple)
def generate_services(*general_services, yearly_services=(), monthly_services=(), months=12):
    monthly_services = tuple(monthly_services)
    yearly_services = tuple(yearly_services) + general_services
    all_services = monthly_services + yearly_services

    if not all(isinstance(service, Service) for service in all_services):
        raise ValueError('All service must be Service objects!', all_services)

    # First month, dump everything
    yield all_services

    # Then, yield the remaining services
    for month in range(1, 12):
        yield monthly_services

@_apply(list)
def run_simulation(POS, HDHP, simulations):
    plans = (('POS', POS), ('HDHP', HDHP))
    for sim_name, sim_services in simulations.items():
        print("For the {} simulation:".format(sim_name))
        for plan_name, plan in plans:
            result = tuple(plan(sim_services))[-1]
            yield result

            print("  {} Plan results:".format(plan_name))
            print("  Net cost to employee over year: ${}".format(result.year_total))
            print("  Net cost less premiums over year: ${}".format(result.year_service))
            print("  Remaining employer contribution: ${}\n".format(result.coverage_remaining))

