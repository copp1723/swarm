module.exports = {
    testEnvironment: 'jsdom',
    testMatch: ['<rootDir>/**/*.test.js'],
    transform: {
        '^.+\\.js$': 'babel-jest'
    },
    testEnvironmentOptions: {
        url: 'http://localhost:5006'
    },
    collectCoverageFrom: [
        'agents/**/*.js',
        'components/**/*.js',
        'services/**/*.js',
        'utils/**/*.js',
        '!**/*.test.js',
        '!**/*.map.js'
    ],
    coverageDirectory: 'coverage',
    coverageReporters: ['text', 'lcov', 'html']
};

