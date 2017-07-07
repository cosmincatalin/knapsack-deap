import random

from deap import creator, base, tools, algorithms


class Solver(object):

    NGEN = 50
    MU = 50
    LAMBDA = 100
    CXPB = 0.7
    MUTPB = 0.2
    SEED = 42

    def __init__(self, items, max_volume):
        self.items = items
        self.max_volume = max_volume

    def eval_knapsack(self, individual):
        volume = 0
        value = 0
        for item in individual:
            volume += self.items[item][0]
            value += self.items[item][1]
        if volume > self.max_volume:
            return 10000, 0
        return volume, value

    # noinspection
    @staticmethod
    def cx_set(ind1, ind2):
        temp = set(ind1)
        ind1 &= ind2
        ind2 ^= temp
        return ind1, ind2

    def mut_set(self, individual):
        if random.random() < 0.5:
            if len(individual) > 0:  # We cannot pop from an empty set
                individual.remove(random.choice(sorted(tuple(individual))))
        else:
            individual.add(random.randrange(len(self.items)))
        return individual,

    def solve(self):

        creator.create("Fitness", base.Fitness, weights=(-1.0, 1.0))
        creator.create("Individual", set, fitness=creator.Fitness)

        initial_size = int(max(1, min(len(self.items), self.max_volume) // 2))

        toolbox = base.Toolbox()
        toolbox.register("attr_item", random.randrange, len(self.items))
        toolbox.register("individual", tools.initRepeat, creator.Individual, toolbox.attr_item, initial_size)
        toolbox.register("population", tools.initRepeat, list, toolbox.individual)
        toolbox.register("evaluate", self.eval_knapsack)
        toolbox.register("mate", self.cx_set)
        toolbox.register("mutate", self.mut_set)
        toolbox.register("select", tools.selNSGA2)

        random.seed(self.SEED)

        pop = toolbox.population(n=self.MU)
        hof = tools.ParetoFront()

        algorithms.eaMuPlusLambda(pop, toolbox, self.MU, self.LAMBDA, self.CXPB, self.MUTPB, self.NGEN,
                                  halloffame=hof, verbose=False)
        return hof[-1]
