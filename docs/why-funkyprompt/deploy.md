---
description: How to deploy to Kubernetes
---

# Deploy

The reason we will deploy `funkyprompt` is  we want to have a served version of the agent and we want to create ingestion jobs to continue to ingest data on the server.

{% hint style="info" %}
There are many ways to deploy and use funkyprompt. One of the easiest might be to add the library to your existing services that you deploy so you do not need any extra deployment overhead. However, You can deploy a standalone test instance in the following way.
{% endhint %}

### Option 1 (Recommended): Deploy as an Argo-CD Application set

To deploy to a Kubernetes cluster you need to have an [Argo-CD](https://argo-cd.readthedocs.io/en/stable/) instance running on your cluster and Argo Workflows also installed in order to run the workflows.&#x20;

{% hint style="info" %}
If you do not have these Argo projects on your cluster it is very easy and recommended that you install them. However you can still deploy your own deployment without the workflows
{% endhint %}

`funkyprompt` uses [Buildpacks](https://buildpacks.io/) to create semantically versioned containers on every build in Git.&#x20;

#### 1 building your own image

You can build your own image by building from the repo.&#x20;

**You should install** [pack](https://buildpacks.io/docs/tools/pack/) utility and then if you have **cloned the repo** locally as described in the [install.md](install.md "mention") section then you can run the following command from the repo root

<pre class="language-bash"><code class="lang-bash"><strong>#from the cloned funkyprompt repo having installed [pack]
</strong><strong>pack build --builder paketobuildpacks/builder:base \
</strong>           --publish &#x3C;your-container-registry.io>/funkyprompt:&#x3C;your-tag>    \
           --cache-image   &#x3C;your-container-registry.io>/funkyprompt:&#x3C;your-tag>-cache
</code></pre>

#### 2 deploying an application to your cluster

In the `funkyprompt` repo there is an [example](https://github.com/mr-saoirse/funkyprompt/tree/main/deploy) of how to deploy the application. You can push that to your own cluster with your own docker image.&#x20;

_2.1 Edit the image  in application-set.yaml_

```yaml
 ...
 kustomize:
    commonAnnotations:
      app/param-host: "bla"
    images:
      - EDIT_IMAGE_TO_BE_THE_ONE_YOU_BUILT
```

_2.2 Apply the application to your cluster_

```
kubernetes apply -f ./deploy/application-set.yaml -n argo
```

_2.2 Open a port to Argo CD server and browse to localhost:8080_

```
kubectl port-forward svc/argocd-server 8080:80
```

{% hint style="info" %}
You should see an application as shown below - names etc may&#x20;
{% endhint %}

<figure><img src="../.gitbook/assets/Screenshot 2023-10-26 at 6.12.36 PM.png" alt=""><figcaption><p>a deployed funky app</p></figcaption></figure>

_3.3 Now you can check that you can connect to the Funky API app_

```
#open a port and browse locally - localhost:8008
kubectl port-forward svc/mother-app-service 8008:8008 - n argo
```

The swagger docs should appear and you can do some things such as interact with the RAG systems as discussed next.

### Option 2: Deploy the deployment standalone and add the workflow separately

#### 1 building your own image

_This first "pack" step the same as what we did at the start of Option 1._

**You should install** [pack](https://buildpacks.io/docs/tools/pack/) utility and then if you have **cloned the repo** locally as described in the [install.md](install.md "mention") section then you can run the following command from the repo root

<pre class="language-bash"><code class="lang-bash"><strong>#from the cloned funkyprompt repo having installed [pack]
</strong><strong>pack build --builder paketobuildpacks/builder:base \
</strong>           --publish &#x3C;your-container-registry.io>/funkyprompt:&#x3C;your-tag>    \
           --cache-image   &#x3C;your-container-registry.io>/funkyprompt:&#x3C;your-tag>-cache
</code></pre>

#### 2 deploying an application to your cluster (without Argo CD)

Now that you have an image, you can deploy the manifests directly to Kubernetes. In this case, if you do not have Argo-CD or do not wish to create an Application in Argo, you can use `kustomize` and kubectl directly to simply deploy the application. You should change the image and tag in the `kustomize` [file](https://github.com/mr-saoirse/funkyprompt/blob/main/deploy/apps/mr-funky/kustomization.yaml) to match the version that you built above in the "pack" step.

_**Note**: The app bundle has an Argo_ [_Workflow_](https://github.com/mr-saoirse/funkyprompt/blob/main/deploy/apps/mr-funky/uber-workflow.yaml) _so you still need to have an instance of_ [_Argo Workflows_](https://argoproj.github.io/argo-workflows/) _on your cluster (this is different to Argo-CD). If you do not need it, you can remove it from the application._

```bash
# after editing the image/tag in the kustomize file
# optional edit the app name to mrs-funky
kubectl apply -k mr-funky
```

_Open a port to Argo CD server and browse to localhost:8080_

```
kubectl port-forward svc/argocd-server 8080:80
```
