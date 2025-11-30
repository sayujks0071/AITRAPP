const { kiteService } = require('./services/kiteService');
const token = kiteService.getAccessToken();
if (token) {
  console.log(token);
} else {
  console.error('No token available');
  process.exit(1);
}
