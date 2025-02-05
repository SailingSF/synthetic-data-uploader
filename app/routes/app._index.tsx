import { useState } from "react";
import type { ActionFunctionArgs, LoaderFunctionArgs } from "@remix-run/node";
import { useFetcher } from "@remix-run/react";
import {
  Page,
  Layout,
  Text,
  Card,
  Button,
  BlockStack,
  Box,
  Select,
  TextField,
  Banner,
} from "@shopify/polaris";
import { TitleBar } from "@shopify/app-bridge-react";
import { authenticate } from "../shopify.server";

type ActionResponse = 
  | { success: true; data: any; error?: never }
  | { success: false; error: string; data?: never };

export const loader = async ({ request }: LoaderFunctionArgs) => {
  await authenticate.admin(request);
  return null;
};

export const action = async ({ request }: ActionFunctionArgs) => {
  const { session } = await authenticate.admin(request);
  
  const formData = await request.formData();
  const dataType = formData.get("dataType");
  const count = formData.get("count");

  try {
    // Call local FastAPI backend
    const response = await fetch("http://localhost:8000/generate", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        type: dataType,
        count: parseInt(count as string),
        shop_access_token: session.accessToken,
      }),
    });

    if (!response.ok) {
      throw new Error("Failed to generate data");
    }

    const result = await response.json();
    return { success: true, data: result } as ActionResponse;
  } catch (error) {
    if (error instanceof Error) {
      return { success: false, error: error.message } as ActionResponse;
    }
    return { success: false, error: "An unknown error occurred" } as ActionResponse;
  }
};

export default function Index() {
  const fetcher = useFetcher<ActionResponse>();
  const [dataType, setDataType] = useState("products");
  const [count, setCount] = useState("10");

  const isLoading = fetcher.state !== "idle";

  const handleGenerate = () => {
    fetcher.submit(
      { dataType, count },
      { method: "POST" }
    );
  };

  return (
    <Page>
      <TitleBar title="Synthetic Data Generator" />
      <BlockStack gap="500">
        <Layout>
          <Layout.Section>
            <Card>
              <BlockStack gap="400">
                <Text as="h2" variant="headingMd">
                  Generate Synthetic Data
                </Text>
                <Text variant="bodyMd" as="p">
                  Use this tool to generate synthetic data for your Shopify store. Choose the type of data
                  and the number of items you want to generate.
                </Text>

                <Select
                  label="Data Type"
                  options={[
                    {label: "Products", value: "products"},
                    {label: "Customers", value: "customers"},
                    {label: "Orders", value: "orders"}
                  ]}
                  onChange={setDataType}
                  value={dataType}
                />

                <TextField
                  label="Number of items"
                  type="number"
                  value={count}
                  onChange={setCount}
                  autoComplete="off"
                />

                <Button
                  onClick={handleGenerate}
                  loading={isLoading}
                >
                  Generate Data
                </Button>

                {fetcher.data && (
                  <Banner
                    title={fetcher.data.success ? "Success!" : "Error"}
                    tone={fetcher.data.success ? "success" : "critical"}
                  >
                    <p>
                      {fetcher.data.success
                        ? `Successfully generated ${count} ${dataType}`
                        : `Error: ${fetcher.data.error}`}
                    </p>
                  </Banner>
                )}

                {fetcher.data?.success && fetcher.data.data && (
                  <Box
                    padding="400"
                    background="bg-surface-active"
                    borderWidth="025"
                    borderRadius="200"
                    borderColor="border"
                    overflowX="scroll"
                  >
                    <pre style={{ margin: 0 }}>
                      <code>
                        {JSON.stringify(fetcher.data.data, null, 2)}
                      </code>
                    </pre>
                  </Box>
                )}
              </BlockStack>
            </Card>
          </Layout.Section>
        </Layout>
      </BlockStack>
    </Page>
  );
}
