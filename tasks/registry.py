# Task registry — maps task_name → run(payload, progress_cb) callable
# Tasks are grouped into category subpackages:
#   monte_carlo/     heat_diffusion/     linear_algebra/
#   physics/         fluid_network/      additional/

from tasks.monte_carlo import pi_estimation, option_pricing, random_walk, integration
from tasks.heat_diffusion import diffusion_1d, diffusion_2d, chemical, population_spread
from tasks.linear_algebra import matrix_multiply, eigenvalues, svd, pca
from tasks.physics import projectile, lotka_volterra, pendulum, spring_mass
from tasks.fluid_network import fluid_advection, network_spread, traffic_flow, forest_fire
from tasks.additional import (
    diffusion_reaction,
    quantum_well,
    brownian_motion,
    heat_conduction_varying,
    fractal_dla,
    wave_propagation,
    population_genetics,
    epidemic_sir,
    game_of_life,
    financial_risk_mc,
)

TASK_REGISTRY: dict = {
    # ── Monte Carlo Simulations ──────────────────────────────────────────────
    "monte_carlo_pi":           pi_estimation.run,        # 1
    "option_pricing":           option_pricing.run,       # 2
    "random_walk":              random_walk.run,          # 3
    "monte_carlo_integration":  integration.run,          # 4

    # ── Heat & Diffusion ─────────────────────────────────────────────────────
    "heat_diffusion_1d":        diffusion_1d.run,         # 5
    "heat_diffusion_2d":        diffusion_2d.run,         # 6
    "chemical_diffusion":       chemical.run,             # 7
    "population_spread":        population_spread.run,    # 8

    # ── Linear Algebra ───────────────────────────────────────────────────────
    "matrix_multiply":          matrix_multiply.run,      # 9
    "eigenvalue_decomp":        eigenvalues.run,          # 10
    "svd_decomposition":        svd.run,                  # 11
    "pca_covariance":           pca.run,                  # 12

    # ── Physics / Kinematics ─────────────────────────────────────────────────
    "projectile_motion":        projectile.run,           # 13
    "lotka_volterra":           lotka_volterra.run,       # 14
    "pendulum_motion":          pendulum.run,             # 15
    "spring_mass":              spring_mass.run,          # 16

    # ── Fluid / Network ──────────────────────────────────────────────────────
    "fluid_advection":          fluid_advection.run,      # 17
    "network_spread":           network_spread.run,       # 18
    "traffic_flow":             traffic_flow.run,         # 19
    "forest_fire":              forest_fire.run,          # 20

    # ── Additional ───────────────────────────────────────────────────────────
    "diffusion_reaction":       diffusion_reaction.run,   # 21
    "quantum_well":             quantum_well.run,         # 22
    "brownian_motion":          brownian_motion.run,      # 23
    "heat_conduction_varying":  heat_conduction_varying.run,  # 24
    "fractal_dla":              fractal_dla.run,          # 25
    "wave_propagation":         wave_propagation.run,     # 26
    "population_genetics":      population_genetics.run,  # 27
    "epidemic_sir":             epidemic_sir.run,         # 28
    "game_of_life":             game_of_life.run,         # 29
    "financial_risk_mc":        financial_risk_mc.run,    # 30
}

# TASK_METADATA: name → {description, default_payload}
# Consumed by GET /tasks to expose available tasks to clients.
TASK_METADATA: dict[str, dict] = {
    # ── Monte Carlo Simulations ──────────────────────────────────────────────
    "monte_carlo_pi": {
        "description": "Estimate π via Monte Carlo random sampling.",
        "default_payload": {"iterations": 1_000_000},
    },
    "option_pricing": {
        "description": "Price a European call option via Black-Scholes Monte Carlo.",
        "default_payload": {"S": 100, "K": 100, "T": 1.0, "r": 0.05, "sigma": 0.2, "simulations": 500_000},
    },
    "random_walk": {
        "description": "Simulate N particles performing a random walk in D dimensions.",
        "default_payload": {"steps": 1_000, "particles": 100, "dimensions": 2},
    },
    "monte_carlo_integration": {
        "description": "Numerically integrate a function over [0,1]^D via Monte Carlo.",
        "default_payload": {"samples": 1_000_000, "dimensions": 3},
    },
    # ── Heat & Diffusion ─────────────────────────────────────────────────────
    "heat_diffusion_1d": {
        "description": "Solve 1-D heat diffusion via explicit finite differences.",
        "default_payload": {"grid_size": 200, "steps": 5_000, "diffusion_coeff": 0.1},
    },
    "heat_diffusion_2d": {
        "description": "Solve 2-D heat diffusion on a square grid.",
        "default_payload": {"grid_size": 50, "steps": 500, "diffusion_coeff": 0.1},
    },
    "chemical_diffusion": {
        "description": "Simulate chemical species diffusion with a source term.",
        "default_payload": {"grid_size": 100, "steps": 2_000, "diffusion_coeff": 0.05},
    },
    "population_spread": {
        "description": "Model population dispersal via diffusion on a 2-D landscape.",
        "default_payload": {"grid_size": 80, "steps": 1_000, "growth_rate": 0.1},
    },
    # ── Linear Algebra ───────────────────────────────────────────────────────
    "matrix_multiply": {
        "description": "Benchmark dense matrix multiplication (NxN).",
        "default_payload": {"size": 512},
    },
    "eigenvalue_decomp": {
        "description": "Compute eigenvalues and eigenvectors of a random symmetric matrix.",
        "default_payload": {"size": 256},
    },
    "svd_decomposition": {
        "description": "Compute the full SVD of a random MxN matrix.",
        "default_payload": {"rows": 512, "cols": 256},
    },
    "pca_covariance": {
        "description": "Run PCA on a random dataset and return explained variance ratios.",
        "default_payload": {"n_samples": 1_000, "n_features": 50, "n_components": 10},
    },
    # ── Physics / Kinematics ─────────────────────────────────────────────────
    "projectile_motion": {
        "description": "Simulate projectile motion with air resistance.",
        "default_payload": {"velocity": 50.0, "angle": 45.0, "drag_coeff": 0.01},
    },
    "lotka_volterra": {
        "description": "Integrate predator-prey (Lotka-Volterra) ODEs.",
        "default_payload": {"alpha": 0.1, "beta": 0.02, "gamma": 0.3, "delta": 0.01, "steps": 10_000},
    },
    "pendulum_motion": {
        "description": "Simulate a nonlinear pendulum via Runge-Kutta integration.",
        "default_payload": {"length": 1.0, "angle": 2.0, "steps": 20_000},
    },
    "spring_mass": {
        "description": "Solve a damped spring-mass system over time.",
        "default_payload": {"mass": 1.0, "spring_k": 10.0, "damping": 0.5, "steps": 10_000},
    },
    # ── Fluid / Network ──────────────────────────────────────────────────────
    "fluid_advection": {
        "description": "Advect a scalar field using a 2-D velocity field (finite differences).",
        "default_payload": {"grid_size": 100, "steps": 1_000, "velocity": 0.5},
    },
    "network_spread": {
        "description": "Simulate information/disease spread on a random graph (SIR on network).",
        "default_payload": {"nodes": 500, "edges": 2_000, "steps": 100},
    },
    "traffic_flow": {
        "description": "Simulate Nagel-Schreckenberg cellular automaton traffic flow.",
        "default_payload": {"road_length": 200, "n_cars": 80, "steps": 1_000},
    },
    "forest_fire": {
        "description": "Run a stochastic forest-fire cellular automaton on a 2-D grid.",
        "default_payload": {"grid_size": 100, "steps": 500, "p_grow": 0.05, "p_ignite": 0.001},
    },
    # ── Additional ───────────────────────────────────────────────────────────
    "diffusion_reaction": {
        "description": "Simulate the Gray-Scott diffusion-reaction system in 2-D.",
        "default_payload": {"grid_size": 80, "steps": 2_000, "Du": 0.16, "Dv": 0.08, "f": 0.035, "k": 0.065},
    },
    "quantum_well": {
        "description": "Solve time-independent Schrödinger equation for a finite square well.",
        "default_payload": {"n_points": 1_000, "well_depth": 50.0, "well_width": 2.0},
    },
    "brownian_motion": {
        "description": "Simulate Brownian motion of N particles and compute mean-squared displacement.",
        "default_payload": {"particles": 200, "steps": 1_000, "dimensions": 2},
    },
    "heat_conduction_varying": {
        "description": "1-D heat conduction with spatially varying thermal conductivity.",
        "default_payload": {"grid_size": 200, "steps": 5_000},
    },
    "fractal_dla": {
        "description": "Grow a Diffusion-Limited Aggregation (DLA) fractal cluster.",
        "default_payload": {"grid_size": 200, "n_particles": 2_000},
    },
    "wave_propagation": {
        "description": "Solve the 2-D wave equation via finite differences.",
        "default_payload": {"grid_size": 100, "steps": 500, "c": 1.0},
    },
    "population_genetics": {
        "description": "Simulate genetic drift and selection in a finite population (Wright-Fisher).",
        "default_payload": {"population": 500, "generations": 1_000, "alleles": 10},
    },
    "epidemic_sir": {
        "description": "Run a stochastic SIR epidemic model on a population.",
        "default_payload": {"population": 10_000, "beta": 0.3, "gamma": 0.05, "steps": 365},
    },
    "game_of_life": {
        "description": "Run Conway's Game of Life on a random initial grid.",
        "default_payload": {"grid_size": 100, "steps": 500},
    },
    "financial_risk_mc": {
        "description": "Compute portfolio VaR and CVaR via Monte Carlo simulation.",
        "default_payload": {"n_assets": 10, "simulations": 100_000, "horizon": 252},
    },
}
