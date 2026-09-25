const rateLimit = require('express-rate-limit');

// Rate limiting for API Endpoints (excluding WebSockets as they have their own limits)
const apiLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // Limit each IP to 100 requests per windowMs
  standardHeaders: true, // Return rate limit info in the `RateLimit-*` headers
  legacyHeaders: false, // Disable the `X-RateLimit-*` headers
  message: { error: 'Too many requests from this IP, please try again after 15 minutes' }
});

const authLimiter = rateLimit({
  windowMs: 60 * 60 * 1000, // 1 hour
  max: 10, // Limit each IP to 10 login/auth requests per windowMs
  message: { error: 'Too many authentication attempts, please try again after an hour' }
});

module.exports = {
  apiLimiter,
  authLimiter
};
