-- Runs once, when the database container is first created: a separate
-- database for the tests, so they never touch your real data
CREATE DATABASE easyweight_test OWNER easyweight;
