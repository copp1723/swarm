module.exports = {
    testEnvironment: 'jsdom',
    setupFilesAfterEnv: ['<rootDir>/tests/setup.js'],
    testMatch: ['<rootDir>/tests/**/*.test.js'],
    moduleNameMapping: {
        '^../(.*)$': '<rootDir>/$1',
        '^./(.*)$': '<rootDir>/$1'
    },
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

