#' Bayesian Nowcast
#'
#' Sequential Bayesian updating of a quarterly forecast as intra-quarter signals
#' arrive. Each signal is a noisy observation with its own precision; the posterior
#' is a conjugate Normal update over a Normal prior from `historical`.
#'
#' @param historical numeric vector of past quarterly outcomes (defines prior mean/sd)
#' @param signals list of named signal observations: each has value and weight (0-1)
#' @param day_of_quarter integer (optional, for uncertainty-reduction reporting)
#' @return list with point_estimate, ci_95, posterior_sd, interpretation

run_nowcast <- function(historical, signals, day_of_quarter = NA_integer_) {
  hist <- as.numeric(historical)
  hist <- hist[is.finite(hist)]
  if (length(hist) < 4) {
    return(list(error = "Need at least 4 historical observations for prior", n_hist = length(hist)))
  }

  prior_mu <- mean(hist)
  prior_sd <- stats::sd(hist)
  if (!is.finite(prior_sd) || prior_sd <= 0) prior_sd <- max(1e-6, abs(prior_mu) * 0.1)

  mu <- prior_mu
  sd_post <- prior_sd
  n_signals <- 0L

  if (is.list(signals) && length(signals) > 0) {
    for (nm in names(signals)) {
      s <- signals[[nm]]
      val <- suppressWarnings(as.numeric(s$value))
      wt  <- suppressWarnings(as.numeric(s$weight))
      if (!is.finite(val) || !is.finite(wt) || wt <= 0 || wt > 1) next
      signal_sd <- prior_sd * sqrt(1 / wt - 1 + 1e-6)
      var_post <- 1 / (1 / sd_post^2 + 1 / signal_sd^2)
      mu <- var_post * (mu / sd_post^2 + val / signal_sd^2)
      sd_post <- sqrt(var_post)
      n_signals <- n_signals + 1L
    }
  }

  ci_low <- mu - 1.96 * sd_post
  ci_high <- mu + 1.96 * sd_post
  reduction <- 1 - (sd_post / prior_sd)

  interpretation <- sprintf(
    "Nowcast point estimate %.3f (95%% CI [%.3f, %.3f]). Posterior SD %.3f vs prior SD %.3f — uncertainty reduced by %.1f%% after %d signals.%s",
    mu, ci_low, ci_high, sd_post, prior_sd, 100 * reduction, n_signals,
    if (!is.na(day_of_quarter)) sprintf(" (day %d of quarter)", day_of_quarter) else ""
  )

  list(
    prior_mean = prior_mu,
    prior_sd = prior_sd,
    point_estimate = mu,
    posterior_sd = sd_post,
    ci_95 = c(ci_low, ci_high),
    uncertainty_reduction = reduction,
    n_signals = n_signals,
    interpretation = interpretation
  )
}
