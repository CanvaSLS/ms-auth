'use strict';

// Serverless v3 crea el stage desde Deployment, sin AWS::ApiGateway::Stage.
// Declarar límites en StageDescription evita SDK post-deploy y roles extra.
module.exports = class AcademyStage {
  constructor(serverless) {
    this.hooks = {
      'after:package:compileEvents': () => {
        const resources = serverless.service.provider.compiledCloudFormationTemplate.Resources;
        const deployments = Object.values(resources).filter(
          (resource) => resource.Type === 'AWS::ApiGateway::Deployment'
        );
        if (deployments.length !== 1) throw new Error('Se esperaba un deployment REST');
        const limits = serverless.service.custom.throttling;
        deployments[0].Properties.StageDescription = {
          ThrottlingBurstLimit: limits.burstLimit,
          ThrottlingRateLimit: limits.rateLimit,
        };
      },
    };
  }
};
