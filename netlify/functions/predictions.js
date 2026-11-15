// Netlify Serverless Function: predictions.js
// Returns empty list by default so new user sessions start fresh with no previous mock records.

exports.handler = async (event, context) => {
  return {
    statusCode: 200,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*'
    },
    body: JSON.stringify([])
  };
};
