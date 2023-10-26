---
description: How to deploy to Kubernetes
---

# Deploy

The reason we will deploy `funkyprompt` is  we want to have a served version of the agent and we want to create ingestion jobs to continue to ingest data on the server.

There are many ways to deploy and use funkyprompt. One of the easiest might be to add the library to your existing services. However, You can deploy a standalone test instance in the following way.

### Option 1: Deploy as an Argo-CD Application set

`funkyprompt` uses Buikdpack to create semantically versioned containers on every build in Git. To deploy to a Kubernetes cluster you need to have an Argo-CD instance running on your cluster and Argo Workflows also installed in order to run the workflows. If you do not have these you could deploy as a deployment but we do not discuss that here.

{% hint style="info" %}
If you do not have these Argo projects on your cluster it is very easy and recommended that you install them. However you can still deploy your own deployment without the workflows
{% endhint %}

1 Build with pack and take note of the image tag

```
// Some code
```

&#x20;2 Deploy the application to your cluster (todo test with kustomize)

```
kubernetes apply -f ./k8s/application-set.yaml -n argo
```

3 Open a port to the server swagger docs

```
// Some code
```
